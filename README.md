# Text2SPARQL
## Table of Contents
- [Introduction and fatures](#introduction_and_features)
- [Setting](#Setting)
- [Install and run](#Install_and_run)

## Introduction and Features
The provided Python script is designed for querying a knowledge graph through
SPARQL queries. It leverages the capabilities of the `QueryRunner` class from the
`sparql_utils.knowledgeGraphSearch` module. The script is structured to be an
executable program with a primary focus on querying a knowledge graph and
processing the retrieved information. It is capable of handling both relation-based and
text-based queries.
The script begins by defining prefix aliases, which are used to simplify the use of
namespaces or vocabulary terms within SPARQL queries. These aliases make the
queries more readable and concise. The primary purpose of the script is to execute a
specific query, and it initializes a `QueryRunner` object, specifying the URL of the
SPARQL server and the prefixes.
The heart of the script revolves around the `runQuery` method, which is part of the
`QueryRunner` class. This method performs the following key tasks:
1. Concurrent Query Execution: It uses multithreading to execute relation and text
searches concurrently, aiming to expedite the query process.
2. Merging Results: After executing both relation and text searches, the script merges
the results from these two modes. This step is essential for gathering a comprehensive
set of results.
3.Result Filtering: It removes undesirable or "bad" links from the merged results. This
is achieved by matching query tokens with the available links to improve result quality.
4. Entity Information Retrieval: The script retrieves detailed information about the
result entities, which includes similar entities, categories, ontology links, income
entities, and outcome entities. It also calculates scored categories based on ontology
links and category links.
5. Final Result Composition: The final results are structured as a dictionary, containing
information about the mode used in relation and text searches and a list of entities with
their respective information.

This script, designed for querying knowledge graphs, offers the potential to uncover
meaningful insights and relationships within complex data structures. It demonstrates
the capabilities of the `QueryRunner` class for querying and processing data from a
knowledge graph. It's important to note that the specifics of the queries, the knowledge
graph schema, and the nature of the results depend on the underlying implementation
of the knowledge graph system. Further understanding and customization of the script would require detailed knowledge of the specific knowledge graph and its data
structure.

## Setting
Go to the directory containing the `initializer.py` file and configure the initializer like so:
```
from SPARQLQueryRunner import QueryRunner

# Create an instance of QueryRunner
query_runner = QueryRunner(url_sparql_server='your_sparql_server_url', prefixes={'entity': 'your_entity_prefix', 'category': 'your_category_prefix', 'type': 'your_type_prefix'})

# Run a query
result = query_runner.runQuery('your_query_text')

# Print the result
print(result)
```

## Install and Run
1. **Install Docker:**
   Begin by downloading and installing [Docker](https://www.docker.com/) from the official Docker website.
2. Download python:3.8.5 image as base.
3. In the terminal, navigate to the directory containing the `docker-compose.yml` file and run:

    ```bash
    docker-compose up -d
    ```