import json
import requests
import synapseclient
from synapseclient import EntityViewSchema, EntityViewType, Synapse
syn  = synapseclient.Synapse()

import sys

fileview = sys.argv[1]
webhook_url = sys.argv[2]
token = sys.argv[3]

syn.login(password = token)


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
    # Add columns for user, project name, and parent folder name
    df['userName'] = ''
    df['projectName'] = ''
    df['parentFolderName'] = ''

    for index, row in df.iterrows():
        # Get user info
        user = syn.getUserProfile(row['modifiedBy'])
        df.at[index, 'userName'] = user['userName']

        # Get project info
        project = syn.get(row['projectId'], downloadFile=False)
        df.at[index, 'projectName'] = project.name

        # Get parent folder info
        parent_folder = syn.get(row['parentId'], downloadFile=False)
        df.at[index, 'parentFolderName'] = parent_folder.name

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



count = find_modified_entities_fileview(syn, fileview).groupby(['modifiedBy','projectId','parentId']).count().reset_index()

enriched_data = enrich_count(count, syn)

slack_message_blocks = dataframe_to_slack_block_with_md_links(enriched_data)

# Usage
send_message_to_slack_blocks(webhook_url, slack_message_blocks)


