# TODO: Make it check files in pub folders and exclude files that are in a code_gpt.ignore file.

import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate


load_dotenv()

chat_llm = ChatOpenAI(model_name="gpt-4", openai_api_key=os.getenv('OPENAI_API_KEY'), temperature=0)

description_features = """
Your description must cover, in highly precise and accurate detail, the following elements:
1. All of the imports used. You should exactly copy the imports from the code.
2. All of the algorithms the code uses, include descriptions of code flows and any decisions that are made.
3. Clearly identify any function calls that occur within the code, be precise about any parameters (and their order) or callbacks that are used.
4. Any function definition along with their input parameters, return types, and an explanation of their purpose. You should state the order of parameters for functions and methods.
5. Precisely list all variables used in the file. Provide the datatypes and uses of each. If any variables are created then describe exactly how.
6. Explain how the code interacts with external APIs, services, or other systems.
7. Error handling and edge cases: Describe how the code handles errors and edge cases, including any relevant logging or monitoring strategies.
8. Any additional hints or guidance to ensure the generated code matches the original code.
9. A detailed natural language description of this file, your thoughts on it and instructions that you would give to a human or AI to reconstruct the file. Take advantage of natural language to explain concepts within the codebase that aren't easily explainable in raw code.
"""

response_schemas = [
    ResponseSchema(name="observation", description="observation about the task"),
    ResponseSchema(name="action", description="actions taken to complete the task"),
    ResponseSchema(name="description", description="description of the code file"),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

def get_code_file_summary_prompt():
    system_template = """You're are provided with the following information about a programming file:
filename: {filename}
path: {path}
code: 
```
{code}
```
{description_features}

Your response must be in the following format:
{format_instructions}
"""
    return ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template(system_template)  
    ],
    input_variables=["filename", "path", "code", "description_features"],
    partial_variables={"format_instructions": format_instructions}
)


def process_file(input_folder, output_folder, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            code = file.read()
            path = os.path.relpath(file_path, input_folder)
            filename = os.path.basename(file_path)

            prompt = get_code_file_summary_prompt()
            _input = prompt.format_prompt(filename=filename, path=path, code=code, description_features=description_features)

            output = chat_llm(_input.to_messages())
            parsed_output = output_parser.parse(output.content)

            print("Code summary")
            print(parsed_output['description'])
            print("--------------------------------")

            os.makedirs(output_folder, exist_ok=True)
            output_file_name = f"{os.path.splitext(filename)[0]}_summary.txt"
            output_file_path = os.path.join(output_folder, output_file_name)

            with open(output_file_path, "w", encoding="utf-8") as summary_file:
                summary_file.write(parsed_output['description'])

    except Exception as e:
        print(f"Error with the following file: {filename}")
        print(e)

def process_directory(input_folder, output_folder):
    for root, _, files in os.walk(input_folder):
        if "node_modules" not in root:
            for file in files:
                print("checking file", file)
                if file.endswith(('.js', '.jsx', '.ts', '.tsx', 'package.json', '.css', '.scss', '.py', '.html', '.rs', 'Cargo.toml')):
                    file_path = os.path.join(root, file)
                    process_file(input_folder, output_folder, file_path)

def generate_system_schematic(input_folder, output_folder=None):
    print("starting process")
    if output_folder is None:
        output_folder = os.path.join(input_folder, "outputs")
    os.makedirs(output_folder, exist_ok=True)
    process_directory(input_folder, output_folder)

if __name__ == "__main__":
    input_folder = os.getcwd()
    generate_system_schematic(input_folder)