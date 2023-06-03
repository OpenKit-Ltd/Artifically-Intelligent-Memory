import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
import asyncio
import time

load_dotenv()

chat_llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=os.getenv('OPENAI_API_KEY'), temperature=0)

response_schemas = [
    ResponseSchema(name="observation", description="observation about the task."),
    ResponseSchema(name="action", description="action to be taken to complete the task."),
    ResponseSchema(name="code_summary", description="your code summary following the format described above."),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()




def get_code_review_prompt():
    system_template = """You have over 10 years in the software development industry. You have build up reliable heuristics on how software should be developed for optimum company efficiency.

You work for a software development company as a code reviewer. You are an expert at reviewing code from a variety of programming languages. You have an intricate and detailed understanding of how software development and coding work especially in large teams on production level enterprise software.

You have the ability to simulate the running of functions in a virtual environment powered by language, you will use this ability to perform unit tests on files. You know that the results of these simulations may not be accurate.

Your goal will be to provide intimate and detailed feedback on a coding file you are presented with, this will help the user improve their coding ability, identify bugs and errors and to maximize the efficiency of company operations.

You're are provided with the following information about a programming file:
filename: {filename}
path: {path}
code: 
```
{code}
```

You must produce a report for the user containing the following elements:
1. A detailed code review as if you were a Tech Lead reviewing one of your team. Consider including if it meets best practices, error handing, edge cases, efficiency.
2. A simulated run of the code to determine if it will run successfully with a valid output, you must describe each step of your simulation and provide output logs.
3. A final statement of whether the code is acceptable to be deployed to production.

Your response must be in the following format:
{format_instructions}
"""
    return ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template(system_template)  
    ],
    input_variables=["filename", "path", "code"],
    partial_variables={"format_instructions": format_instructions}
)



def get_code_file_summary_prompt():
    system_template = """You're are provided with the following information about a programming file:

You are an expert at software development. You are an expert at Python. You are an expert at Javascript and Typescript. You are an expert at software engineering. 

You are an expert at converting a code file into structured, technical, code summary which allows the code to be understood at a semantic level.

Your task with be to generate a structured, technical, code summary of the file you are provided.

filename: {filename}
path: {path}
code: 
```
{code}
```

You must follow this standardized format template for your structured, technical, code summary:
1. All of the imports used. You should exactly copy the imports from the code.
2. All of the algorithms the code uses, include descriptions of code flows and any decisions that are made.
3. Clearly identify any function calls that occur within the code, be precise about any parameters (and their order) or callbacks that are used.
4. Any function definition along with their input parameters, return types, and an explanation of their purpose. You should state the order of parameters for functions and methods.
5. Precisely list all variables used in the file. Provide the datatypes and uses of each. If any variables are created then describe exactly how.
6. Explain how the code interacts with external APIs, services, or other systems.
7. Error handling and edge cases: Describe how the code handles errors and edge cases, including any relevant logging or monitoring strategies.
8. Any additional hints or guidance to ensure the generated code matches the original code.
9. A detailed natural language description of this file, your thoughts on it and instructions that you would give to a human or AI to reconstruct the file. Take advantage of natural language to explain concepts within the codebase that aren't easily explainable in raw code.

Your response must be in the following format:
{format_instructions}
"""
    return ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template(system_template)  
    ],
    input_variables=["filename", "path", "code"],
    partial_variables={"format_instructions": format_instructions}
)

def process_file(input_folder, output_folder, file_path, processed_files):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            code = file.read()
            path = os.path.relpath(file_path, input_folder)
            filename = os.path.basename(file_path)

            # Check if the output file already exists
            output_file_name = f"{os.path.splitext(filename)[0]}_summary.txt"
            output_file_path = os.path.join(output_folder, output_file_name)
            if os.path.exists(output_file_path):
                print(f"Skipping the following file (already in outputs folder): {filename}")
                # Store the original file path in the dictionary even if skipped
                processed_files[output_file_name] = file_path
                return

            prompt = get_code_file_summary_prompt()
            _input = prompt.format_prompt(filename=filename, path=path, code=code)
            output = chat_llm(_input.to_messages())
            parsed_output = output_parser.parse(output.content)

            if not parsed_output['code_summary'].strip():
                print(f"No summary generated for the following file: {filename}")
                return

            print("Code summary")
            print(parsed_output['code_summary'])
            print("--------------------------------")

            os.makedirs(output_folder, exist_ok=True)

            # Save the output as soon as the LLM response comes back
            with open(output_file_path, "w", encoding="utf-8") as summary_file:
                summary_file.write(parsed_output['code_summary'])

            # Store the original file path in the dictionary
            processed_files[output_file_name] = file_path

    except Exception as e:
        print(f"Error with the following file: {filename}")
        print(e)

def process_directory(input_folder, output_folder, processed_files):
    for root, _, files in os.walk(input_folder):
        if "node_modules" not in root:
            for file in files:
                if (file.endswith(('.js', '.jsx', '.ts', '.tsx', 'package.json', '.css', '.scss', '.py', '.html', '.rs', 'Cargo.toml'))
                    and file != "code_gpt.py"):
                    print("checking file", file)
                    file_path = os.path.join(root, file)
                    process_file(input_folder, output_folder, file_path, processed_files)

def write_summary_to_combined_file(combined_summary_file, original_file_path, summary_file_path):
    original_filename = os.path.splitext(os.path.basename(original_file_path))[0]

    # Write filename and path
    combined_summary_file.write(f"Filename: {original_filename}\n")
    combined_summary_file.write(f"Path: {original_file_path}\n\n")

    # Write code
    with open(original_file_path, "r", encoding="utf-8") as original_file:
        code = original_file.read()
        combined_summary_file.write("Code:\n```\n")
        combined_summary_file.write(code)
        combined_summary_file.write("\n```\n\n")

    # Write explanation
    with open(summary_file_path, "r", encoding="utf-8") as individual_summary:
        explanation = individual_summary.read()
        combined_summary_file.write("Explanation:\n")
        combined_summary_file.write(explanation)
        combined_summary_file.write("\n\n" + "-" * 80 + "\n\n")

def generate_system_schematic(input_folder, output_folder=None):
    print("starting process")
    if output_folder is None:
        output_folder = os.path.join(input_folder, "outputs")
    os.makedirs(output_folder, exist_ok=True)

    # Create a dictionary to store original file paths
    processed_files = {}

    process_directory(input_folder, output_folder, processed_files)

    # Combine all summaries into a single file
    combined_summary_file_path = os.path.join(output_folder, "combined_summary.txt")
    with open(combined_summary_file_path, "w", encoding="utf-8") as combined_summary_file:
        for summary_file in os.listdir(output_folder):
            if summary_file.endswith("_summary.txt"):
                summary_file_path = os.path.join(output_folder, summary_file)

                # Check if the summary file exists in the processed_files dictionary
                if summary_file not in processed_files:
                    print(f"Skipping the following file (not found in processed files): {summary_file}")
                    continue

                original_file_path = processed_files[summary_file]

                # Write the summary to the combined file
                write_summary_to_combined_file(combined_summary_file, original_file_path, summary_file_path)

if __name__ == "__main__":
    input_folder = "./"
    generate_system_schematic(input_folder)