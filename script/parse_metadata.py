# script/parse_metadata.py
import json
import os
import sys

def main():
    json_str = os.environ.get('ADDITIONAL_JSON_INPUT')
    output_args = []

    if json_str:
        try:
            data = json.loads(json_str)
            for key, value in data.items():
                # Ensure values are safely converted to string
                # And handle potential spaces in values by quoting them for shell
                # Using single quotes for shell, escaping any internal single quotes
                safe_value = str(value).replace("'", "'\\''")
                output_args.append(f"--metadata={key}:'{safe_value}'")
            # Print the flags to stdout, which will be captured by the shell script
            print('ADDITIONAL_METADATA_FLAGS=' + ' '.join(output_args))
        except json.JSONDecodeError as e:
            # Use GitHub Actions' error logging syntax for clear output to stderr
            print(f"::error::Error decoding JSON for additional_metadata_json: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # If no JSON input, still output the variable name, but with no flags
        # This ensures the shell script doesn't try to parse an empty string
        print('ADDITIONAL_METADATA_FLAGS=')

if __name__ == "__main__":
    main()