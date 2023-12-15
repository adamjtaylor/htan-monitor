# README.md for HTAN Monitor

## Overview

This tool is designed to monitor activity in a specified Synapse fileview. It checks for any entities modified within a set time frame and sends an update to a Slack channel. This is particularly useful for teams using Synapse for collaborative projects, as it keeps everyone informed about the latest changes.

## Features

- **Synapse Integration**: Connects to Synapse to access fileview data.
- **Slack Notifications**: Sends daily updates to a designated Slack channel.
- **Customizable Time Frames**: Allows for setting specific intervals for monitoring changes.
- **User-Friendly Updates**: Formats Slack messages with Markdown for easy reading.

## Requirements

- Python 3.x
- Synapse account with access to the desired fileview.
- Slack webhook URL for sending notifications.

## Environment Variables

- `FILEVIEW`: Synapse Fileview ID to monitor.
- `WEBHOOK`: Slack webhook URL for sending notifications.
- `SCHEDULED_JOB_SECRETS`: JSON containing Synapse authentication token.

## Usage

### Local

1. Install Python 3.x if not already installed.
2. Clone or download this repository.
3. Install required packages: `pip install -r requirements.txt`.
4. Run the script: `python synapse_fileview_script.py {fileview_synid} {slack_webhook_url}`

### Docker

A docker container is automatically built and pushed to GCHR when changes are made to this repo.

1. Pull the Docker image:

    ```{bash}
    docker pull ghcr.io/ncihtan/htan-monitor:latest
    ```

2. Run the Docker container

    ```{bash}
    docker run \
        -e FILEVIEW={fileview_synid} \
        -e WEBHOOK={slack_webhook_url} \
        -e SYNAPSE_AUTH_TOKEN={synapse_auth_token} \
        ghcr.io/ncihtan/htan-monitor:latest
    ```

### AWS Scheduled Job

Set up an AWS Scheduled Job with the following parameters

1. Image: `ghcr.io/ncihtan/htan-monitor:latest`
2. Command: `python ./monitor.py ${FILEVIEW} ${WEBHOOK}`
3. Secrets: `SYNAPSE_AUTH_TOKEN={synapse_auth_token}`
4. EnvVars: `FILEVIEW={fileview_synid},WEBHOOK={slack_webhook_url}`
5. Schedule: (to run daily at 0800 UTC): `cron(0 8 * * ? *)`

## Functions

- `synapse_login()`: Authenticates and connects to Synapse.
- `find_modified_entities_fileview()`: Retrieves entities modified within a specified time frame.
- `enrich_count()`: Enriches data with additional details from Synapse.
- `dataframe_to_slack_block_with_md_links()`: Formats the data into Slack message blocks with Markdown links.
- `send_message_to_slack_blocks()`: Sends the formatted message to Slack.

## Contributing

Contributions are welcome. Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers directly.
