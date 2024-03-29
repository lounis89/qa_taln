"""TALN.py
TP Conception et implémentation d’un système de
questions réponses en langue naturelle sur des données structurées
"""

import math
import re
import spacy
from lxml import etree
from nltk.metrics import *
from SPARQLWrapper import JSON, SPARQLWrapper

LANGUAGE = "en"

nlp = spacy.load("en_core_web_sm")
tokenizer = nlp.tokenizer

questions = []
reponsesAttendues = []
reponses = []

# Parsing XML du fichier questions.xml
tree = etree.parse("./questions.xml")
root = tree.getroot()

# Récupérer les questions
for q in root.findall("question/string"):
    question = q.text
    lang = q.get("lang")

    if lang == LANGUAGE:
        questions.append(str(question))

# Récupérer les réponses URI
for a in root.findall("question/answers/answer/uri"):
    answer = a.text
    reponses.append(a.text)


# REGEX sur le token du pronom intérrogatif
def reponseAttendue(token):
    """
    The reponseAttendue function is used to determine the type of question that was asked.
    It takes a token as an argument and checks if it matches any of the regular expressions for each type of question.
    If there is a match, then it appends the corresponding tag to reponsesAttendues list.

    :param token: Match the question with a reponseattendue
    :return: The type of the question
    """

    if re.match(r"[Ww]ho", token):
        reponsesAttendues.append("PERS")
    elif re.match(r"[Ww]here", token):
        reponsesAttendues.append("GEO")
    elif re.match(r"[Ww]hen", token):
        reponsesAttendues.append("TIM")
    else:
        reponsesAttendues.append("")


# Trouver l'entité nommé pour une question donnée
def NER(question):
    """
    The NER function takes a question as input and returns the entity that is being asked about.

    :param question: Find the entity in the question
    :return: named entity
    """

    ner = ""
    doc = nlp(question)
    for ent in doc.ents:
        ner = ent.text  # On récupère l'entité nommé par Spacy
    if len(ner) == 0:  # Si Spacy ne trouve l'entité nommé
        ner = "NOT_FOUND"

    # Traitement sur l'entité nommé pour préparer la requête
    ner = str(ner).replace("the ", "")
    ner = str(ner).replace(" ", "_")
    return ner


# Retourner la relation avec la distance de Levenshtein la plus proche des mots de la phrases
def relationsAvec(question):
    """
    The relationsAvec function takes a question as an input and returns the relation that is closest to the question.
    The function uses Levenshtein distance to find the relation that is closest to the question.

    :param question: Find the relation of a question
    :return: The relation of the question
    """

    tokens = []
    doc = nlp(question)
    for token in doc:
        tokens.append(token.text)
    min_score = math.inf
    relation = None
    with open("relations.txt") as f:
        for line in f:
            line = line.replace("\n", "")
            line_compare = re.sub(r"([a-z].*):", "", line)
            for token in tokens:
                score = edit_distance(token, line_compare)
                if score < min_score:
                    min_score = score
                    relation = line
    return relation


# Préparation et envoie d'une requête vers DBpedia
def requête(relation, entite):
    """
    The requête function accomplishes the following:
        1. It takes in a relation and an entity as arguments.
        2. It then queries DBPedia to find all entities that are related by the given relation to the given entity,
           returning them as a list of URIs (strings).

    :param relation: Know what is the relation between the two entities
    :param entite: Specify the entity we want to find relations for
    :return: A json object
    """
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query = "PREFIX dbo: <http://dbpedia.org/ontology/> PREFIX res: <http://dbpedia.org/resource/> SELECT DISTINCT ?uri WHERE { res:"
    query += entite + " " + relation + " ?uri . }"
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()
    return result


#### Traitement des questions #####
tab_result = []
for question in questions:
    doc = nlp(question)
    for i, token in enumerate(doc):
        if i == 0:  # PRONOM INTERROGATIF EN DEBUT DE PHRASE
            reponseAttendue(token.text)

    if NER(question) != "NOT_FOUND":
        results = requête(relationsAvec(question), NER(question))
    for result in results["results"]["bindings"]:
        tab_result.append(result["uri"]["value"])


def recall(reponses, tab_result):
    """
    The recall function takes in two parameters: reponses and tab_result.
    It then checks if the result is in the list of responses, and increments a counter for every correct answer.
    Finally it returns the number of correct answers divided by the length of reponses.

    :param reponses: Store the list of correct answers
    :param tab_result: Store the result of the prediction
    :return: The number of correct answers divided by the total number of questions
    """

    nb_correct = 0
    for res in tab_result:
        if res in reponses:
            nb_correct += 1
    return nb_correct / len(reponses)


def precision(tab_result):
    """
    The precision function takes a list of results and returns the precision of those results.
    The precision is calculated by dividing the number of correct answers by the total number
    of answers.

    :param tab_result: Store the result of a test
    :return: The proportion of correct answers in the tab_result
    """

    nb_correct = 0
    for res in tab_result:
        if res in reponses:
            nb_correct += 1
    return nb_correct / len(tab_result)


def fmeasure(recall, precision):
    """
    The fmeasure function is a helper function that calculates the fmeasure score for a given precision and recall value.
    The fmeasure score is defined as: 2 * (precision * recall) / (precision + recall).


    :param recall: Determine the number of relevant results
    :param precision: Measure the accuracy of the positive predictions
    :return: The fmeasure, which is a combination of the precision and recall
    """

    return (2 * precision * recall) / (precision + recall)


recall = recall(reponses, tab_result)
precision_metric = precision(tab_result)
fmeasure = fmeasure(recall, precision_metric)

print("(---- Evaluation du système de questions et réponses en langage naturel ----)")
print("      Rappel du sytème : " + str(recall))
print("      Précision du système : " + str(precision_metric))
print("      F-measure : " + str(fmeasure))
print("(---------------------------------------------------------------------------)")
