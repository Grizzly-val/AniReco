import json

# Open the JSON file in read mode ('r') using a 'with' statement
try:
    with open('sample.json', 'r') as file:
        # Use json.load() to deserialize the file data into a Python object
        data = json.load(file)

    # The 'data' variable is now a Python dictionary (based on the JSON structure)
    print("Successfully imported JSON data:")
    print(f"Data type: {type(data)}")

    # Access specific elements using dictionary keys or list indices
    print(f"\nAccessing specific data:")
    print(f"Size: {len(data["data"])}")

except FileNotFoundError:
    print("Error: The file 'data.json' was not found.")
except json.JSONDecodeError:
    print("Error: Failed to decode JSON from the file. Check for malformed JSON data.")
