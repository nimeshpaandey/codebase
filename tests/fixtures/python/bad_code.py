import os

# Known Bug 1: Mutable default argument (Correctness)
def add_item(item, items=[]):
    items.append(item)
    return items

def execute_user_command(user_cmd):
    try:
        # Known Bug 2: Insecure eval() execution (Security)
        result = eval(user_cmd)
        return result
    # Known Bug 3: Bare except (Reliability)
    except:
        pass
    return None

if __name__ == "__main__":
    print(add_item("a"))
