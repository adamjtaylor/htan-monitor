import json
import requests
import synapseclient
from synapseclient import EntityViewSchema, EntityViewType, Synapse

import sys
import os
from tqdm import tqdm


if os.getenv("FILEVIEW") is not None:
    fileview = os.getenv("FILEVIEW")
else:
    fileview = sys.argv[1]

if os.getenv("WEBHOOK") is not None:
    webhook_url = os.getenv("WEBHOOK")
else:
    webhook_url = sys.argv[2]

def synapse_login(synapse_config=synapseclient.client.CONFIG_FILE):
    """Login to Synapse.  Looks first for secrets.

    Args:
        synapse_config: Path to synapse configuration file.
                        Defaults to ~/.synapseConfig

    Returns:
        Synapse connection
    """
    syn = synapseclient.Synapse(skip_checks=True)
    if os.getenv("SCHEDULED_JOB_SECRETS") is not None:
        secrets = json.loads(os.getenv("SCHEDULED_JOB_SECRETS"))
        syn.login(silent=True, authToken=secrets["SYNAPSE_AUTH_TOKEN"])
    else:
        syn.login(silent=True)
    return syn


def find_modified_entities_fileview(
    syn: Synapse, syn_id: str, value: int = 1, unit: str = "day"
) -> list:
    """Finds entities scoped in a fileview modified in the past {value} {unit}

    Args:
        syn: Synapse connection
        syn_id: Synapse Fileview Id
        value: number of time units
        unit: time unit

    Returns:
        List of synapse ids
    """
    # Update the view
    # _force_update_view(syn, view_id)

    query = (
        f"select id, projectId, parentId, createdBy, modifiedBy, Component from {syn_id} where "
        f"modifiedOn > unix_timestamp(NOW() - INTERVAL {value} {unit})*1000"
    )
    results = syn.tableQuery(query)
    resultsdf = results.asDataFrame()
    return resultsdf


def enrich_count(df, syn):
    """
    Enriches a DataFrame with user names, project names, and parent folder names from Synapse.

    Args:
        df (pd.DataFrame): DataFrame containing Synapse data with columns 'modifiedBy', 'projectId', and 'parentId'.
        syn (synapseclient.Synapse): A logged-in Synapse client instance.

    Returns:
        pd.DataFrame: The enriched DataFrame.
    """
    # Initialize columns for user, project name, and parent folder name
    df['userName'] = ''
    df['projectName'] = ''
    df['parentFolderName'] = ''

    # Initialize caches for users, projects, and folders
    user_cache = {}
    project_cache = {}
    folder_cache = {}

    # Wrap iterrows with tqdm for a progress bar
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Enriching Data"):
        # Get or cache user info
        user_id = row['modifiedBy']
        if user_id not in user_cache:
            user_cache[user_id] = syn.getUserProfile(user_id)['userName']
        df.at[index, 'userName'] = user_cache[user_id]

        # Get or cache project info
        project_id = row['projectId']
        if project_id not in project_cache:
            project_cache[project_id] = syn.get(project_id, downloadFile=False).name
        df.at[index, 'projectName'] = project_cache[project_id]

        # Get or cache parent folder info
        folder_id = row['parentId']
        if folder_id not in folder_cache:
            folder_cache[folder_id] = syn.get(folder_id, downloadFile=False).name
        df.at[index, 'parentFolderName'] = folder_cache[folder_id]

    return df

    
def dataframe_to_slack_block_with_md_links(df):
    base_synapse_url = "https://www.synapse.org/#!Synapse:"
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "*Your daily update on HTAN activity on Synapse:*"}}]
    for index, row in df.iterrows():
        # Determine the correct pluralization
        dataset_text = "dataset" if row['id'] == 1 else "datasets"
        
        # Construct the Markdown URL for the parent folder
        parent_folder_url = f"{base_synapse_url}{row['parentId']}"
        parent_folder_link = f"<{parent_folder_url}|{row['parentFolderName']}>"
                
        # Format the line with the Markdown link
        line = f"{row['userName']} modified {row['id']} {dataset_text} in the {parent_folder_link} folder of the {row['projectName']} project."
        block = {"type": "section", "text": {"type": "mrkdwn", "text": f"{line}"}}
        blocks.append(block)
    return {"blocks": blocks}


def send_message_to_slack_blocks(webhook_url, blocks):
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(blocks)
    response = requests.post(webhook_url, headers=headers, data=data)
    if response.status_code != 200:
        raise ValueError(f"Request to slack returned an error {response.status_code}, the response is:\n{response.text}")

syn = synapse_login()

count = find_modified_entities_fileview(syn, fileview).groupby(['modifiedBy','projectId','parentId']).count().reset_index()

enriched_data = enrich_count(count, syn)

# Check if the dataframe is empty
if enriched_data.empty:
    # If no modified entities are found, prepare a simple message for Slack
    slack_message_blocks = {
        "blocks": [
            {
                "type": "section", 
                "text": {
                    "type": "mrkdwn", 
                    "text": "No entities were modified in the last day"
                }
            }
        ]
    }
else:
    # If there are modified entities, format the message as before
    slack_message_blocks = dataframe_to_slack_block_with_md_links(enriched_data)

# Usage
send_message_to_slack_blocks(webhook_url, slack_message_blocks)


