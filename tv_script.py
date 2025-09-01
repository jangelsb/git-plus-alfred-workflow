import sys
import random
import json
import os

def get_env_variable(var_name):
    return os.environ.get(var_name)

def run(argv):
    sentences = [
        "Fruits are the seed-bearing structures in flowering plants.",
        "Vegetables are parts of plants that are consumed by humans as food.",
        "The apple is a sweet fruit that grows on an apple tree.",
        "Carrots are root vegetables that are typically orange in color.",
        "Bananas are tropical fruits with soft flesh and yellow skins.",
        "Tomatoes are botanically fruits but often treated as vegetables.",
        "Kale is a leafy green vegetable rich in nutrients.",
        "Strawberries are red fruits known for their sweet flavor.",
        "Peppers can be sweet or spicy and come in various colors.",
        "Broccoli is a healthy vegetable that's high in vitamins."
    ]

    typed_query = argv[1] if len(argv) > 1 else None

    x = get_env_variable("tv_command")

    sentence = x or typed_query or random.choice(sentences)

    result = {
        "variables": {
            "command": "banana",
            "option": "carrot",
            "alt": "apple"
        },
        "response": f"```\n{sentence}\n```",
        "footer": "Anatomy of fruits and vegetables",
        "behaviour": {
            "response": "append",
            "scroll": "end",
            "inputfield": "clear"
        }
    }
    
    return json.dumps(result)

if __name__ == "__main__":
    print(run(sys.argv))