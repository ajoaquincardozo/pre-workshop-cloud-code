import os
import traceback
import json
import re
import argparse
from dotenv import load_dotenv

def load_env_config():
    load_dotenv()
    return {
        "DEFINITION_PATH": os.getenv("DEFINITION_PATH")
    }

def get_files_by_extension(directory, extension):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(extension):
                files.append(os.path.join(root, filename))
    return files

def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}\n"

def write_content_to_file(content, output_file):
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"Error writing to {output_file}: {str(e)}")
        return False

def extend_layer_content(base_content, directory, regex_patterns, file_extension='.cs'):
    extended_content = base_content
    for file_path in get_files_by_extension(directory, file_extension):
        if any(re.search(pattern, file_path) for pattern in regex_patterns):
            file_content = read_file_content(file_path)
            if file_extension == '.cs':
                extended_content += f"// File: {file_path}\n{file_content}\n\n"
            else:
                extended_content += f"# File: {file_path}\n{file_content}\n\n"
    return extended_content

def process_layer(directory, file_patterns=None, file_extension='.cs'):
    content = ''
    if file_patterns:
        return extend_layer_content('', directory, file_patterns, file_extension)

    for file_path in get_files_by_extension(directory, file_extension):
        file_content = read_file_content(file_path)
        if file_extension == '.cs':
            content += f"// File: {file_path}\n{file_content}\n\n"
        else:
            content += f"# File: {file_path}\n{file_content}\n\n"
    return content

def process_kustomize_files(solution_path, definition, results_folder):
    deploy_folder = os.path.join(results_folder, 'deploy', 'kustomize')
    source_base = os.path.join(solution_path, 'deploy', 'kustomize', 'base')
    source_overlays = os.path.join(solution_path, 'deploy', 'kustomize', 'overlays')
    service_name = definition.get('name', 'unnamed')

    processed_layers = []
    error_log = []

    def combine_yaml_files(directory, parent_path=''):
        combined_content = []
        if not os.path.exists(directory):
            return "", [f"Directory not found: {directory}"]

        for root, _, files in os.walk(directory):
            for file in sorted(files):
                if file.endswith(('.yaml', '.yml')):
                    file_path = os.path.join(root, file)
                    content = read_file_content(file_path)
                    if content:
                        full_path = os.path.join(parent_path, os.path.relpath(file_path, directory))
                        combined_content.append(f"# Source: deploy/kustomize/{full_path}")
                        combined_content.append(content.strip())
                        combined_content.append("---")

        return "\n".join(combined_content), []

    # Process base files
    base_content, base_errors = combine_yaml_files(source_base, 'base')
    if base_content:
        base_output = os.path.join(deploy_folder, f"{service_name}_base.yaml")
        if write_content_to_file(base_content, base_output):
            processed_layers.append("deploy/kustomize/base")
        else:
            error_log.append("Error writing base yaml file")
    error_log.extend(base_errors)

    # Process overlays directories
    overlay_content = []
    for env in ['production', 'staging']:
        env_path = os.path.join(source_overlays, env)
        env_content, env_errors = combine_yaml_files(env_path, f'overlays/{env}')
        if env_content:
            overlay_content.append(f"# Environment: {env}")
            overlay_content.append(env_content)
        error_log.extend(env_errors)

    if overlay_content:
        overlays_output = os.path.join(deploy_folder, f"{service_name}_overlays.yaml")
        combined_overlays = "\n".join(overlay_content)
        if write_content_to_file(combined_overlays, overlays_output):
            processed_layers.append("deploy/kustomize/overlays")
        else:
            error_log.append("Error writing overlays yaml file")

    return processed_layers, error_log

def analyze_solution(solution_path, definition):
    layers = {
        'Domain.Core': process_layer,
        'Domain.Entities': process_layer,
        'Infrastructure': process_layer,
        'Presentation.Api': process_layer
    }

    error_log = []
    processed_layers = []

    analysis_name = definition.get('name', 'unnamed')
    results_folder = os.path.join('analysis_results', analysis_name)

    # Process source files
    src_folder = os.path.join(results_folder, 'src')
    for layer in definition['layers']:
        layer_path = os.path.join(solution_path, 'src', layer)
        if os.path.exists(layer_path):
            try:
                file_patterns = None
                if not definition.get('process_all_files', True):
                    if 'files_to_process' in definition and layer in definition['files_to_process']:
                        file_patterns = [item['path'] for item in definition['files_to_process'][layer]]
                    else:
                        continue

                content = process_layer(layer_path, file_patterns)
                output_file = os.path.join(src_folder, f'{analysis_name}_src_{layer}.cs')

                if write_content_to_file(content, output_file):
                    print(f"Created {output_file}")
                    processed_layers.append(f"src/{layer}")
                else:
                    error_log.append(f"Error writing combined file for src/{layer}")
            except Exception as e:
                error_message = f"Error processing src/{layer}: {str(e)}\n{traceback.format_exc()}"
                print(error_message)
                error_log.append(error_message)
        else:
            error_log.append(f"Project folder not found: src/{layer}")

    # Process test files
    test_folder = os.path.join(results_folder, 'test')
    for layer in definition['layers']:
        test_paths = [
            os.path.join(solution_path, 'test', f"{layer}.Test"),
            os.path.join(solution_path, 'test', f"{layer}.Tests"),
            os.path.join(solution_path, 'tests', f"{layer}.Test"),
            os.path.join(solution_path, 'tests', f"{layer}.Tests")
        ]

        test_layer_path = None
        for path in test_paths:
            if os.path.exists(path):
                test_layer_path = path
                break

        if test_layer_path:
            try:
                file_patterns = None
                if not definition.get('process_all_files', True):
                    if 'files_to_process' in definition and layer in definition['files_to_process']:
                        file_patterns = [item['path'] for item in definition['files_to_process'][layer]]
                    else:
                        continue

                content = process_layer(test_layer_path, file_patterns)
                output_file = os.path.join(test_folder, f'{analysis_name}_test_{layer}.cs')

                if write_content_to_file(content, output_file):
                    print(f"Created {output_file}")
                    processed_layers.append(f"test/{layer}")
                else:
                    error_log.append(f"Error writing combined file for test/{layer}")
            except Exception as e:
                error_message = f"Error processing test/{layer}: {str(e)}\n{traceback.format_exc()}"
                print(error_message)
                error_log.append(error_message)

    # Process deploy files
    deploy_layers, deploy_errors = process_kustomize_files(solution_path, definition, results_folder)
    processed_layers.extend(deploy_layers)
    error_log.extend(deploy_errors)

    print("\nProcessing Summary:")
    print(f"Results saved in: {results_folder}")
    print(f"Analysis name: {analysis_name}")
    print(f"Successfully processed projects: {', '.join(processed_layers)}")
    if error_log:
        print("\nErrors encountered:")
        for error in error_log:
            print(f"- {error}")
    else:
        print("No errors encountered during processing.")

def load_definition(definition_path):
    default_definition = {
        "name": "unnamed",
        "solution_path": "./",
        "layers": [
            "Domain.Core",
            "Domain.Entities",
            "Infrastructure",
            "Presentation.Api"
        ],
        "process_all_files": True,
        "files_to_process": {}
    }

    if definition_path:
        try:
            with open(definition_path, 'r') as f:
                user_definition = json.load(f)
                for key, value in user_definition.items():
                    if key in default_definition and isinstance(default_definition[key], dict):
                        default_definition[key].update(value)
                    else:
                        default_definition[key] = value
                return default_definition
        except Exception as e:
            print(f"Error loading definition file: {str(e)}")
            print("Using default definition.")

    return default_definition

if __name__ == "__main__":
    env_config = load_env_config()
    parser = argparse.ArgumentParser(description="Analyze Visual Studio solution")
    parser.add_argument("--definition_path", default=env_config["DEFINITION_PATH"],
                       help="Path to the JSON definition file")
    args = parser.parse_args()
    definition = load_definition(args.definition_path)
    solution_path = definition["solution_path"]
    print(f"Analyzing solution in: {solution_path}")
    print(f"Processing all files: {definition['process_all_files']}")
    analyze_solution(solution_path, definition)