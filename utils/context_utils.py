from utils.json_utils import load_json_safe, save_json_safe

CONTEXT_FILE = "context_history.json"

def load_context():
    return load_json_safe(CONTEXT_FILE)

def save_context(ctx):
    save_json_safe(ctx, CONTEXT_FILE)

def update_context(user_id, text):
    ctx = load_context()
    ctx.setdefault(user_id, []).append(text)
    ctx[user_id] = ctx[user_id][-6:]
    save_context(ctx)

def get_context(user_id):
    return load_context().get(user_id, [])

def is_waiting_review(user_id):
    ctx = get_context(user_id)
    return ctx and ctx[-1] == "__wait_review__"
