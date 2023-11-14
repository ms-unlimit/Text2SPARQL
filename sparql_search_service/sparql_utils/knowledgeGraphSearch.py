from SPARQLWrapper import SPARQLWrapper, JSON
from statistics import mean
from threading import Thread

class QueryRunner:
    def __init__(self, url_sparql_server:str, prefixes: dict):
        """
        Initializes the QueryRunner with a SPARQL server URL.

        Args:
            url_sparql_server (str): The URL of the SPARQL server.
        """

        # Create an instance of SPARQLWrapper and set the SPARQL server URL
        self.sparql_server = SPARQLWrapper(url_sparql_server)

        # Retrieve the mapping of instances to labels
        self.instance2labels = self.__instance2labels()

        # Define the prefixes for entities, categories, and types
        self.prefixes = prefixes

    def runQuery(self, query_text: str):
        """
        Runs a query using both relation search and text search methods, merges the results,
        removes bad links, retrieves entity information, and returns the final result.

        Args:
            query_text (str): The query text to search .

        Returns:
            dict: The final query result containing the relation mode, text mode, and the answer.
              - relation_mode (str): The mode used in the relation search (e.g., 'relationQuery', 'semiRelationQuery', 'error').
              - text_mode (str): The mode used in the text search (e.g., 'likeQuery', 'semiLikeQuery', 'error').
              - answer (list): A list of dictionaries containing the result entities and their information.
                  Each dictionary has the following structure:
                  {
                      'result': entity (str),         # The result entity URI
                      'info': entity_information (dict)   # The information of the entity
                  }
        """
        # Perform relation search and text search
        # self.relation_results = self.relationSearch(query_text, 10)
        # self.text_results = self.textSearch(query_text, 20)

        relation_thread = Thread(target= self.relationSearch, args=(query_text, 10))
        text_thread = Thread(target= self.textSearch, args=(query_text, 20))

        relation_thread.start()
        text_thread.start()

        relation_thread.join()
        text_thread.join()

        # Merge the results from relation search and text search
        merge_results = self.__mergeResults(query_text, self.relation_results['answer'], self.text_results['answer'])

        # Remove bad links from the merged results
        removed_bad_links_result = self.__removeBadLinks(merge_results, query_text)

        # Retrieve entity information for each result entity
        answer = [{'result': entity, 'info': self.__getEntityInformation(entity)} for entity in removed_bad_links_result]

        # Construct the final result dictionary
        result = {
            'relation_mode': self.relation_results['mode'],
            'text_mode': self.text_results['mode'],
            'answer': answer
        }

        return result

    def relationSearch(self, query_text: str, limit: int):
        """
        Searches for entities and their associated relations based on the input query_text.

        Args:
            query_text (str): The input text containing tokens to search .
            limit (int): The maximum number of results to return.

        Returns:
            dict: A dictionary containing the search mode ('relationQuery' or 'semiRelationQuery') and the list of entity URIs.
        """
        try:
            # First, try to execute the relationQuery to get exact matches
            answer = self.relationQuery(query_text, limit)
            mode = 'relationQuery'

            # If no results are found, try semiRelationQuery for partial matches
            if len(answer) == 0:
                answer = self.semiRelationQuery(query_text, limit)
                mode = 'semiRelationQuery'

            # Prepare the result dictionary
            self.relation_results = {"mode": mode, "answer": answer}
            return self.relation_results
        except:
            # If any error occurs during the queries, return an error response
            self.relation_results = {"mode": 'error', "answer": []}
            return self.relation_results

    def relationQuery(self, text: str, limit: int):
        """
        Executes a SPARQL query to find entities whose labels match the tokens in the input text and retrieves the number
        of distinct relations associated with each entity.

        Args:
            text (str): The input text containing tokens to search .
            limit (int): The maximum number of results to return.

        Returns:
            list: A list of entity URIs.
        """
        # Tokenize the input text
        tokens = self.__tokenizer(text)

        # Initialize the SPARQL query
        sparql = 'SELECT ?o (COUNT(DISTINCT ?r) AS ?relationCount) WHERE { ?o rdfs:label ?label . FILTER ('

        # Iterate over the tokens and construct the query condition
        for token in tokens:
            if 'regex' in sparql:
                sparql += ' && regex(?label, "{0}", "i") '.format(token)
            else:
                sparql += ' regex(?label, "{0}", "i") '.format(token)

        # Add the entity prefix and the rest of the query
        sparql += ' && regex(str(?o), CONCAT("^", STR('+self.prefixes['entity']+':))) ) ?s ?r ?o . } GROUP BY ?o ORDER BY DESC(?relationCount) LIMIT ' + str(limit)

        # Execute the query and retrieve the results
        results = self.__runSPARQL(sparql)

        return results

    def semiRelationQuery(self, text: str, limit: int):
        """
        Executes a SPARQL query to find entities whose labels match the tokens in the input text and retrieves the number
        of distinct relations associated with each entity. Supports partial matching of tokens.

        Args:
            text (str): The input text containing tokens to search .
            limit (int): The maximum number of results to return.

        Returns:
            list: A list of entity URIs.
        """
        # Tokenize the input text
        tokens = self.__tokenizer(text)

        # Split tokens into start, middle, and end tokens
        start_tokens = tokens[:-1]
        mid_tokens = tokens[1:-1] if len(tokens) > 2 else []
        end_tokens = tokens[1:]

        # Initialize SPARQL query strings
        sparql1, sparql2, sparql3 = '', '', ''

        # Construct SPARQL query conditions for start tokens
        for token in start_tokens:
            if 'regex' in sparql1:
                sparql1 += ' && regex(?label, "{0}", "i") '.format(token)
            else:
                sparql1 += ' regex(?label, "{0}", "i") '.format(token)

        # Construct SPARQL query conditions for end tokens
        for token in end_tokens:
            if 'regex' in sparql2:
                sparql2 += ' && regex(?label, "{0}", "i") '.format(token)
            else:
                sparql2 += ' regex(?label, "{0}", "i") '.format(token)

        # Construct SPARQL query conditions for middle tokens (if applicable)
        if len(mid_tokens) > 1:
            for token in mid_tokens:
                if 'regex' in sparql3:
                    sparql3 += ' && regex(?label, "{0}", "i") '.format(token)
                else:
                    sparql3 += ' || regex(?label, "{0}", "i") '.format(token)

        # Construct the final SPARQL query
        sparql = 'SELECT ?o (COUNT(DISTINCT ?r) AS ?relationCount) WHERE {?o rdfs:label ?label . FILTER((' + sparql1 + ' || ' + sparql2 + sparql3 + ') && regex(str(?o), CONCAT("^", STR('+self.prefixes['entity']+':))) ) ?s ?r ?o . } GROUP BY ?o ORDER BY DESC(?relationCount) LIMIT ' + str(limit)

        # Execute the query and retrieve the results
        results = self.__runSPARQL(sparql)

        return results

    def textSearch(self, query_text: str, limit: int):
        """
        Performs a text search using both exact and partial matching methods.

        Args:
            query_text (str): The text to search .
            limit (int): The maximum number of results to return.

        Returns:
            dict: A dictionary containing the search mode and the list of matching entity URIs.
        """
        try:
            # Perform an exact match search using likeQuery
            answer = self.likeQuery(query_text, limit)
            mode = 'likeQuery'

            # If no exact matches found, perform a partial match search using semiLikeQuery
            if len(answer) == 0:
                answer = self.semiLikeQuery(query_text, limit)
                mode = 'semiLikeQuery'

            # Create a dictionary to store the search mode and answer
            self.text_results = {"mode": mode, "answer": answer}
            return self.text_results
        except:
            # In case of any error, return an empty result with an error mode
            self.text_results = {"mode": 'error', "answer": []}
            return self.text_results

    def likeQuery(self, text: str, limit: int):
        """
        Executes a SPARQL query to find entities whose labels match the tokens in the input text.

        Args:
            text (str): The input text containing tokens to search .
            limit (int): The maximum number of results to return.

        Returns:
            list: A list of entity URIs.
        """
        # Tokenize the input text
        tokens = self.__tokenizer(text)

        # Initialize the SPARQL query
        sparql = 'SELECT DISTINCT ?o WHERE {?o rdfs:label ?label . FILTER ('

        # Iterate over the tokens and construct the query condition
        for token in tokens:
            if 'regex' in sparql:
                sparql += ' && regex(?label, "{0}", "i") '.format(token)
            else:
                sparql += ' regex(?label, "{0}", "i") '.format(token)

        # Add the entity prefix and limit to the query
        sparql += '&& regex(str(?o), CONCAT("^", STR('+self.prefixes['entity']+':))) ) } LIMIT ' + str(limit)

        # Execute the query and retrieve the results
        results = self.__runSPARQL(sparql)

        return results

    def semiLikeQuery(self, text: str, limit: int):
        """
        Executes a SPARQL query to find entities whose labels partially match the tokens in the input text.

        Args:
            text (str): The input text containing tokens to search .
            limit (int): The maximum number of results to return.

        Returns:
            list: A list of entity URIs.
        """
        # Tokenize the input text
        tokens = self.__tokenizer(text)

        # Split tokens into start, middle, and end tokens
        start_tokens = tokens[:-1]
        mid_tokens = tokens[1:-1] if len(tokens) > 3 else []
        end_tokens = tokens[1:]

        # Initialize SPARQL query strings
        sparql1, sparql2, sparql3 = '', '', ''

        # Construct SPARQL query conditions for start tokens
        for token in start_tokens:
            if 'regex' in sparql1:
                sparql1 += ' && regex(?label, "{0}", "i") '.format(token)
            else:
                sparql1 += ' regex(?label, "{0}", "i") '.format(token)

        # Construct SPARQL query conditions for end tokens
        for token in end_tokens:
            if 'regex' in sparql2:
                sparql2 += ' && regex(?label, "{0}", "i") '.format(token)
            else:
                sparql2 += ' regex(?label, "{0}", "i") '.format(token)

        # Construct SPARQL query conditions for middle tokens (if applicable)
        if len(mid_tokens) > 0:
            for token in mid_tokens:
                if 'regex' in sparql3:
                    sparql3 += ' && regex(?label, "{0}", "i") '.format(token)
                else:
                    sparql3 += ' || regex(?label, "{0}", "i") '.format(token)

        # Combine the query conditions into the final SPARQL query
        sparql = 'SELECT DISTINCT ?o WHERE {?o rdfs:label ?label . FILTER (('+sparql1+' || '+sparql2 + sparql3+') && regex(str(?o), CONCAT("^", STR('+self.prefixes['entity']+':))) ) } LIMIT ' + str(limit)

        # Execute the query and retrieve the results
        results = self.__runSPARQL(sparql)

        return results

    def __instance2labels(self):
        """
        Retrieves a dictionary mapping instances to their labels.

        Returns:
            dict: A dictionary mapping instances to labels.
        """
        instance2labels = {}

        # SPARQL query to select distinct instances and labels
        query = 'SELECT DISTINCT ?instance ?label WHERE { ?instance rdf:type owl:Class. ?instance rdfs:label ?label }'

        # Run the query and retrieve the results
        results = self.__runSPARQL(query, pars=False)['results']['bindings']

        # Extract the instance and label values from the query results and populate the dictionary
        for entry in results:
            instance = entry['instance']['value']
            label = entry['label']['value']
            instance2labels[instance] = label

        return instance2labels

    def __runSPARQL(self, query: str, pars=True):
        """
        Executes a SPARQL query using the SPARQL server and returns the results.

        Args:
            query (str): The SPARQL query to execute.
            pars (bool): Flag indicating whether to parse the results or return them as is.
                         Default is True.

        Returns:
            dict or list: The query results. If pars is True, the results are parsed using
                          the __resultParser method and returned as a list. Otherwise, the
                          results are returned as is, in JSON format.
        """
        # Set the query on the SPARQL server
        self.sparql_server.setQuery(query)

        # Set the return format to JSON
        self.sparql_server.setReturnFormat(JSON)

        # Execute the query and convert the results to JSON
        results = self.sparql_server.query().convert()

        if pars:
            return self.__resultParser(results)
        else:
            return results

    def __resultParser(self, result:dict):
        """
        Parses the result of a SPARQL query.

        Args:
            result (dict): The result dictionary obtained from the SPARQL query.

        Returns:
            list: The parsed result values.
        """
        var_idx = result['head']['vars'][0]
        parsed_result = [i[var_idx]['value'] for i in result['results']['bindings']]
        return parsed_result

    def __tokenizer(self, text: str):
        """
        Tokenizes the input text by splitting it on spaces and filtering out tokens with less than 3 characters.

        Args:
            text (str): The input text to tokenize.

        Returns:
            list: A list of tokens.
        """
        # Split the text into tokens based on spaces
        tokens = text.split(' ')

        # Initialize a temporary list to store valid tokens
        temp = []

        # Iterate over the tokens and filter out tokens with less than 3 characters
        for token in tokens:
            if len(token) > 2:
                temp.append(token)

        return temp

    def __sortingTextPurResults(self, query:str, relation_results:list, text_results:list):
        """
        Sorts and scores the text-based results based on their relevance to the query.

        Args:
            query (str): The query text.
            relation_results (list): List of entity URIs from the relation-based search.
            text_results (list): List of entity URIs from the text-based search.

        Returns:
            list: Sorted list of entity URIs based on their relevance scores.
        """
        txt_pur_scored_results = {}
        tokens = self.__tokenizer(query)

        for text_result in text_results:
            if text_result not in relation_results:
                score = 0
                for token in tokens:
                    if token in text_result:
                        score += 1
                score /= len(text_result)
                txt_pur_scored_results[text_result] = score

        sorted_txt_pur_scored_results = sorted(txt_pur_scored_results.items(), key=lambda x: x[1], reverse=True)
        return [i[0] for i in sorted_txt_pur_scored_results]

    def __mergeResults(self, query_text:str, relation_results:list, text_results:list):
        """
        Merges and sorts the relation-based and text-based results.

        Args:
            query_text (str): The query text.
            relation_results (list): List of entity URIs from the relation-based search.
            text_results (list): List of entity URIs from the text-based search.

        Returns:
            list: Merged and sorted list of entity URIs.
        """
        sorted_text_pur_results = self.__sortingTextPurResults(query_text, relation_results, text_results)

        if len(relation_results) == 0 and len(sorted_text_pur_results) == 0:
            return []
        elif len(relation_results) == 0:
            return sorted_text_pur_results
        elif len(sorted_text_pur_results) == 0:
            return relation_results
        elif len(relation_results) > 2 and len(sorted_text_pur_results) > 2:
            return relation_results[:2] + sorted_text_pur_results[:2] + relation_results[2:] + sorted_text_pur_results[2:]
        elif len(relation_results) > 2:
            return relation_results[:2] + sorted_text_pur_results + relation_results[2:]
        else:
            return relation_results + sorted_text_pur_results

    def __removeBadLinks(self, links:list, query:str):
        """
        Removes bad links based on the query tokens.

        Args:
            links (list): List of links.
            query (str): The query string.

        Returns:
            list: List of good links.
        """
        query_tokens = self.__tokenizer(query)
        good_links = []

        for link in links:
            good = False
            tokens = link[31:].split('_')

            for token in tokens:
                token_clean = token.replace('(', '').replace(')', '').replace('\u200c', '')

                if token_clean in query_tokens:
                    good = True
                    break

            if good:
                good_links.append(link)

        return good_links

    def __getEntityInformation(self, entity_uri:str):
        """
        Retrieves information about an entity based on its URI.

        Args:
            entity_uri (str): The URI of the entity.

        Returns:
            dict: Information about the entity including similar entities, categories, ontology links, income entities,
                  and outcome entities.
        """
        # Construct SPARQL queries to retrieve relevant information

        # Query to retrieve income entities connected to the given entity
        income_entities = 'SELECT DISTINCT ?a WHERE { ?a ?b <' + entity_uri + '>. FILTER (regex(str(?a), CONCAT("^", STR('+self.prefixes['entity']+':)))) }'

        # Query to retrieve outcome entities connected to the given entity
        outcome_entities = 'SELECT DISTINCT ?b WHERE { <' + entity_uri + '> ?a ?b . FILTER (regex(str(?b), CONCAT("^", STR('+self.prefixes['entity']+':)))) }'

        # Query to retrieve categories associated with the given entity
        category = 'SELECT DISTINCT ?b WHERE { <' + entity_uri + '> ?a ?b . FILTER (regex(str(?b), CONCAT("^", STR('+self.prefixes['category']+':)))) }'

        # Query to retrieve ontology links associated with the given entity
        ontology = 'SELECT DISTINCT ?b WHERE { <' + entity_uri + '> '+self.prefixes['type']+' ?b . }'

        # Execute the SPARQL queries to retrieve the results
        category_links = self.__runSPARQL(category)
        ontology_links = self.__runSPARQL(ontology)
        income_entities_links = self.__runSPARQL(income_entities)
        outcome_entities_links = self.__runSPARQL(outcome_entities)

        # Calculate scored categories based on the ontology links and category links
        sorted_category = self.__categoryScoring(ontology_links, category_links)

        # Retrieve similar entities based on the ontology links and scored categories
        similar_entities = [e for e in self.__getSimilarEntries(ontology_links, sorted_category, entity_uri) if e != entity_uri]

        # Calculate the mean category score
        mean_category_score = mean([i[1] for i in sorted_category])

        # Filter the top categories based on the mean category score
        top_category = [i[0] for i in sorted_category if i[1] >= mean_category_score]

        # Organize the retrieved information into a dictionary
        entity_info = {
            'similar_entities': similar_entities,
            'categories': top_category,
            'ontology': ontology_links,
            'income_entities': income_entities_links,
            'outcome_entities': outcome_entities_links
        }

        # Return the entity information
        return entity_info

    def __categoryScoring(self, ontology:list, categories:list):
        """
        Scores the categories based on their similarity to the labels of the given ontology.

        Args:
            ontology (list): List of ontology instances.
            categories (list): List of categories to score.

        Returns:
            list: Sorted list of scored categories, in descending order of similarity scores.
              Each item in the list is a tuple containing the category and its similarity score.
        """
        scored_categories = {}
        labels = self.instance2labels[ontology[0]]

        for category in categories:
            score = 0
            for label in labels:
                if label in category:
                    score += 1
            scored_categories[category] = score / len(category)

        sorted_categories = sorted(scored_categories.items(), key=lambda x: x[1], reverse=True)
        return sorted_categories

    def __getSimilarEntries(self, ontology:list, category:list, entity:str):
        """
        Retrieves similar entries (entities) based on the provided ontology and category.

        Args:
            ontology (list): List of ontology instances.
            category (list): List of scored categories, where each item is a tuple containing the category and its similarity score.
            entity (str): The entity for which similar entries are to be retrieved.

        Returns:
            list: List of similar entities.
        """
        sim_ents, num, sparql, categoriesQL0 = [], 3, "", ""

        for i in range(int(len(ontology))):
            categoriesQL0 += " ?s ?p" + str((i + 1) * 100) + " <" + str(ontology[i]) + ">. "

        if len(category) > 3:
            while num > 0:
                categoriesQL = categoriesQL0
                for i in range(num):
                    categoriesQL += " ?s ?p" + str(i + 1) + " <" + str(category[i][0]) + ">. "
                sparql = "SELECT ?s WHERE {" + categoriesQL + " }"
                sim_ents = list(set(self.__runSPARQL(sparql)))
                sim_ents = [e for e in sim_ents if e != entity]
                num -= 1
                if len(sim_ents) > 1:
                    break
            if len(sim_ents) > 10:
                return sim_ents[:10]
            else:
                return sim_ents
        else:
            sparql = "SELECT ?s WHERE {" + categoriesQL0 + " }"
            sim_ents = self.__runSPARQL(sparql)
            if len(sim_ents) > 10:
                return sim_ents[:10]
            else:
                return sim_ents
