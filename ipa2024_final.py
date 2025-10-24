#######################################################################################
# Yourname: Panot Liangpiboon
# Your student ID: 66070112
# Your GitHub Repo: https://github.com/iPaonN/IPA2024-Final

#######################################################################################
# 1. Import libraries for API requests, JSON formatting, time, os, (restconf_final or netconf_final), netmiko_final, and ansible_final.
import requests
import os
import time
import json
import ipaddress
import restconf_final
import netmiko_final
import ansible_final

#######################################################################################
# 2. Assign the Webex access token to the variable ACCESS_TOKEN using environment variables.

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
last_method = None

# print("Current working directory:", os.getcwd())
# print("ACCESS_TOKEN value:", repr(ACCESS_TOKEN))

#######################################################################################
# 3. Prepare parameters get the latest message for messages API.

# Defines a variable that will hold the roomId
roomIdToGetMessages = (os.getenv("roomIdToGetMessages"))

last_method = None


while True:
    # always add 1 second of delay to the loop to not go over a rate limit of API calls
    time.sleep(1)

    # the Webex Teams GET parameters
    #  "roomId" is the ID of the selected room
    #  "max": 1  limits to get only the very last message in the room
    getParameters = {"roomId": roomIdToGetMessages, "max": 1}

    # the Webex Teams HTTP header, including the Authoriztion
    getHTTPHeader = {"Authorization": "Bearer " + ACCESS_TOKEN}

# 4. Provide the URL to the Webex Teams messages API, and extract location from the received message.
    
    # Send a GET request to the Webex Teams messages API.
    # - Use the GetParameters to get only the latest message.
    # - Store the message in the "r" variable.
    r = requests.get(
        "https://webexapis.com/v1/messages",
        params=getParameters,
        headers=getHTTPHeader,
    )
    # verify if the retuned HTTP status code is 200/OK
    print("Response status code:", r.status_code)
    print("Response headers:", dict(r.headers))
    print("Response text:", r.text)
    
    if not r.status_code == 200:
        raise Exception(
            "Incorrect reply from Webex Teams API. Status code: {}. Response: {}".format(r.status_code, r.text)
        )

    # get the JSON formatted returned data
    json_data = r.json()

    # check if there are any messages in the "items" array
    if len(json_data["items"]) == 0:
        raise Exception("There are no messages in the room.")

    # store the array of messages
    messages = json_data["items"]
    
    # store the text of the first message in the array
    message = messages[0]["text"]
    print("Received message: " + message)

    # check if the text of the message starts with the magic character "/" followed by your studentID and a space and followed by a command name
    #  e.g.  "/66070123 create"
    if message.startswith("/" + "66070112" + " "):

        # extract the command
        command = message[len("66070112") + 2:]
        print(command)

# 5. Complete the logic for each command

        attachment_path = None
        responseMessage = None
        parts = command.split()

        method = None
        ip = None

        if parts:
            first_token = parts[0].lower()
            if first_token in {"restconf", "netconf"}:
                method = first_token
                last_method = method
                parts = parts[1:]
            else:
                method = last_method
        else:
            responseMessage = "Error: No command provided."

        if method and not parts:
            responseMessage = f"Ok: {method}"

        if responseMessage is None and not method:
            responseMessage = "Error: No method is specified."

        if responseMessage is None and method:
            if parts:
                try:
                    ipaddress.IPv4Address(parts[0])
                except ipaddress.AddressValueError:
                    pass
                else:
                    ip = parts[0]
                    parts = parts[1:]

            if not parts:
                responseMessage = "Error: No command provided."
            else:
                action = parts[0].lower()

                if method == "restconf":
                    restconf_actions = {"create", "delete", "enable", "disable", "status"}
                    if action in restconf_actions:
                        if not ip:
                            responseMessage = "Error: IP address required for restconf command."
                        else:
                            restconf_final.api_url = f"https://{ip}/restconf/"
                            print(f"Set api_url to: {restconf_final.api_url}")
                            if action == "create":
                                responseMessage = restconf_final.create()
                            elif action == "delete":
                                responseMessage = restconf_final.delete()
                            elif action == "enable":
                                responseMessage = restconf_final.enable()
                            elif action == "disable":
                                responseMessage = restconf_final.disable()
                            elif action == "status":
                                responseMessage = restconf_final.status()
                    elif action == "gigabit_status":
                        responseMessage = netmiko_final.gigabit_status()
                    elif action == "showrun":
                        if not ip:
                            responseMessage = "Error: IP address required for showrun command."
                        else:
                            showrun_result = ansible_final.showrun(ip)
                            response_lines = [showrun_result.get("message", "")]
                            if showrun_result.get("output"):
                                response_lines.append(showrun_result["output"])
                            responseMessage = "\n".join(line for line in response_lines if line)
                            if showrun_result.get("success"):
                                attachment_path = showrun_result.get("file_path")
                    else:
                        responseMessage = "Error: No command or unknown command"
                elif method == "netconf":
                    responseMessage = "NETCONF commands are not implemented yet."

        if responseMessage is None:
            responseMessage = "Error: Unable to process command."
        
# 6. Complete the code to post the message to the Webex Teams room.

        # The Webex Teams POST JSON data for command showrun
        # - "roomId" is is ID of the selected room
        # - "text": is always "show running config"
        # - "files": is a tuple of filename, fileobject, and filetype.

        # the Webex Teams HTTP headers, including the Authoriztion and Content-Type
        
        # Prepare postData and HTTPHeaders for command showrun
        # Need to attach file if responseMessage is 'ok'; 
        # Read Send a Message with Attachments Local File Attachments
        # https://developer.webex.com/docs/basics for more detail

        if attachment_path:
            if not os.path.exists(attachment_path):
                responseMessage = (
                    responseMessage
                    + "\nAttachment missing on controller."
                    if responseMessage
                    else "Attachment missing on controller."
                )
                attachment_path = None

        if attachment_path:
            with open(attachment_path, "rb") as attachment_file:
                data = {
                    "roomId": roomIdToGetMessages,
                    "text": responseMessage or "Ansible backup completed successfully.",
                }
                files = {
                    "files": (
                        os.path.basename(attachment_path),
                        attachment_file,
                        "text/plain",
                    )
                }
                HTTPHeaders = {"Authorization": "Bearer " + ACCESS_TOKEN}
                r = requests.post(
                    "https://webexapis.com/v1/messages",
                    data=data,
                    files=files,
                    headers=HTTPHeaders,
                )
        else:
            postData = {"roomId": roomIdToGetMessages, "text": responseMessage}
            postData = json.dumps(postData)

            HTTPHeaders = {
                "Authorization": "Bearer " + ACCESS_TOKEN,
                "Content-Type": "application/json"
            }

            r = requests.post(
                "https://webexapis.com/v1/messages",
                data=postData,
                headers=HTTPHeaders,
            )
        if not r.status_code == 200:
            raise Exception(
                "Incorrect reply from Webex Teams API. Status code: {}".format(r.status_code)
            )
