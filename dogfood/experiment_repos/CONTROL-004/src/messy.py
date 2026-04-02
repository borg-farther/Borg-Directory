"""Messy Python code with inconsistent formatting."""
def greet(name):
	print(f"Hello, {name}")  # mixed tabs/spaces here
    return True  # trailing whitespace below this line


def calculate_sum(numbers):
    result = 0
  for num in numbers:  # inconsistent indentation (2 spaces)
	    result += num  # tab indentation
	return result


def process_data(data):
    cleaned = []
    for item in data:  # trailing whitespace after this line    
        if item > 0:
            cleaned.append(item * 2)
        else:
            cleaned.append(0)
    return cleaned


def find_max(a, b):
    if a > b:
	    return a
    else:
		    return b


class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x):
        self.value += x

    def subtract(self, x):
        self.value -= x
