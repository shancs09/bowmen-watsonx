# watsonx Orchestrate skills development for Control Testing Automation

This Readme file guides you through setting up of watsonx Orchestrate skills and related IBM Cloud Code Engine applications and functions

## Skills
The necessary OpenAPI specification file and also Code Engine code are available in the Orchestrate/Skills folder. They are arranged by the functionality.
- Orchestrate
  - Skills
    - Get Vendors
    - Get Controls
    - wxai integration - async
    - wxai to table
    - Update OpenPages

## Get IBM Cloud API Key

We will need IBM Cloud API Key to authenticate to OpenPages and watsonx.ai. 

Refer to the [Managing user API keys](https://cloud.ibm.com/docs/account?topic=account-userapikey&interface=ui) for detailed instruction to retrieve your IBM Cloud API Key.

## Steps to deploy CE applications and functions

Clone this GitHub repo to your local machine.

You will find both Code Engine Applications as well as IBM Cloud function code. 

Refer to [Deploying applications on Code Engine](https://cloud.ibm.com/docs/codeengine?topic=codeengine-deploy-app-tutorial) and [Working with Cloud functions](https://cloud.ibm.com/docs/codeengine?topic=codeengine-fun-work) if you need help to deploy following. Keep in mind that 
- You need to set API_KEY environment variable for all the functions and applications
- You need to update API endpoints for OpenPages and watsonx.ai in the Applications and Functions code

Applications/Functions
- Orchestrate
  - Skills
    - Get Vendors
      - Functions
        - get-vendors-list.py
    - Get Controls
      - Functions
        - get-controls-for-vendor.py
    - wxai integration - async
      - CE Code
    - wxai to table
      - CE Code
    - Update OpenPages
      - CE Code

Deploy all the above Applications and Functions. Verify that these application are running fine by calling their API endpoints. Make a note of the endpoints. These will be required to be used in OpenAPI specification files.

Note: watsonx.ai API calls take more than 30 seconds many a times. Due to this, there is timeout on watsonx Orchestrate side. To overcome this issue, skills are made async. So these endpoint behave in a asyncrounous way, meaning as soon as a request is received an immediate response is send that the request is received and parallelly the time consuming task is executed. When the time consuming task completes execution, the response is then send back to watsonx Orchestrate using a callback Url that watsonx Orchestrate sends to the API endpoint in the original request.

## Steps to deploy skills in wxO

You will need to create skills using each of the OpenAPI files listed below. If needed, refer to instructions provided in [Building skills by importing OpenAPI files](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/current?topic=flows-building-skills-by-importing-openapi-files) 

- Orchestrate
  - Skills
    - Get Vendors
      - OpenAPI
        - vendorlist-OpenAPI.json
    - Get Controls
      - OpenAPI
        - get-controls-list.json
    - wxai integration - async
      - OpenAPI
        - async-wx-ai.json
    - wxai to table
      - OpenAPI
        - wxai-to-table.json
    - Update OpenPages
      - OpenAPI
        - update-test-results-to-OP.json

For each of the skills you need to add connections to the SkillSets `Personal skills` and `Orchestrate Agent skillset` and also to `AI agent configuration` -> `Apps and skills`

Note: The following skills are async skills. 
- wxai integration - async
- update-test-results-to-OP.json

Refer to https://www.ibm.com/docs/en/watsonx/watson-orchestrate/current?topic=skills-creating-openapi-specifications#optional-configuring-callback-for-asynchronous-skills to know more on making skills async

## Create skill flow

Create skill flow as shown in the below image

<img src="./images/skill-flow.jpg" alt="Skill flow" width="20%" />

Map inputs from previous skill outputs as appropriate. Many of them are straight forward. One or two might need some help. Attaching screenshot, where helps is needed, below.

<img src="./images/wxai-mapping.png" alt="wxai mapping" width="50%" />

and 

<img src="./images/table-display.png" alt="Table Display" width="50%" />

Add the skill flow in wxO `AI agent configuration` -> `Apps and skills`. Provide a description that will help trigger the user utterances. e.g. `I want to test controls`.

## Run the application end-to-end

In wxO `AI Agent` chat, type you intent. e.g. `I want to test controls` and hit enter. Follow the prompts and select necessary inputs.

## Troubleshooting

1. If any skill is failing to be called then
1.1 Ensure that endpoints of OpenPages and watsonx.ai are up and running
1.2 Check Code Engine application logs for that skill and ensure that it is being called and it returns appropriate data

