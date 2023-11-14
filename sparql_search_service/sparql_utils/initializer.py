from sparql_utils.knowledgeGraphSearch import QueryRunner

query_handler = QueryRunner(
    url_sparql_server='192.168.1.1:port/sparql',
    prefixes={'entity': 'fkgr', 'category': 'fkgc', 'type': 'rdf:instanceOf'})

def update_mode(mode: dict):

    global query_handler
    query_handler = QueryRunner(
        url_sparql_server='192.168.1.1:port/sparql',
        prefixes=mode)
