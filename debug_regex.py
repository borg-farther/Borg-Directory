import re
content = '## Guild Workflow Packs\n\nOld guild content here.\n\n## Other Section\n\nMore stuff.\n'
pattern = r'(\n)?## Guild Workflow Packs.*?(?=\n## |\Z)'
instructions = '\n[NEW GUILD CONTENT]'
new_content = re.sub(pattern, instructions, content, flags=re.DOTALL)
print('Result:', repr(new_content))
print('Old gone?', 'Old guild content' not in new_content)
print('More still there?', 'More stuff' in new_content)
