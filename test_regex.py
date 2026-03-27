import re
pattern = "NoneType has no attribute"
context = "TypeError: 'NoneType' has no attribute 'split'"
print("Pattern:", repr(pattern))
print("Context:", repr(context))
match = re.search(pattern, context)
print("Match:", match)
