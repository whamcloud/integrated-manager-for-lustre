
def set_server_conf(args = None):
    import simplejson as json
    data = json.loads(args.args)
    from hydra_agent.store import AgentStore
    AgentStore.set_server_conf(data)

def remove_server_conf(args = None):
    from hydra_agent.store import AgentStore
    AgentStore.remove_server_conf()
