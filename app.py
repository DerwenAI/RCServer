#!/usr/bin/env python
# encoding: utf-8

from pathlib import Path
from flasgger import Swagger
from flask import Flask, g, jsonify, make_response, redirect, render_template, request
from flask_caching import Cache
from http import HTTPStatus
from richcontext import server as rc_server
import argparse
import json
import sys
import time


DEFAULT_PORT = 5000
DEFAULT_CORPUS = "min_kg.jsonld"


######################################################################
## app definitions

APP = Flask(__name__, static_folder="static", template_folder="templates")
APP.config.from_pyfile("flask.cfg")

CACHE = Cache(APP, config={"CACHE_TYPE": "simple"})
NET = rc_server.RCNetwork()


######################################################################
## page routes

@APP.route("/")
def home_page ():
    return render_template("index.html")


@APP.route("/index.html")
@APP.route("/home/")
def home_redirects ():
    return redirect(url_for("home_page"))


######################################################################
## OpenAPI support

API_TEMPLATE = {
        "swagger": "2.0",
        "info": {
            "title": "Rich Context",
            "description": "OpenAPI for Rich Context microservices",
            "contact": {
                "responsibleOrganization": "Coleridge Initiative",
                "name": "API Support",
                "url": "https://coleridgeinitiative.org/richcontext"
            },
            "termsOfService": "https://coleridgeinitiative.org/computing"
        },
        "basePath": "/",
        "schemes": ["http"],
        "externalDocs": {
            "description": "Documentation",
            "url": "https://github.com/Coleridge-Initiative/rclc/wiki"
        }
    }


SWAGGER = Swagger(APP, template=API_TEMPLATE)


######################################################################
## API routes

@CACHE.cached(timeout=3000)
@APP.route("/api/v1/query/<radius>/<entity>", methods=["GET"])
def api_entity_query (radius, entity):
    """
    query a subgraph for an entity
    ---
    tags:
      - knowledge_graph
    description: 'query with a radius near an entity, using BFS'
    parameters:
      - name: radius
        in: path
        required: true
        type: integer
        description: radius for BFS neighborhood
      - name: entity
        in: path
        required: true
        type: string
        description: entity name to search
    produces:
      - application/json
    responses:
      '200':
        description: neighborhood search within the knowledge graph
    """
    global NET

    t0 = time.time()
    subgraph = NET.get_subgraph(search_term=entity, radius=int(radius))
    hood = NET.extract_neighborhood(subgraph, entity)

    return hood.serialize(t0)


@CACHE.cached(timeout=3000)
@APP.route("/api/v1/links/<index>", methods=["GET"])
def api_entity_links (index):
    """
    lookup the links for an entity
    ---
    tags:
      - knowledge_graph
    description: 'lookup the links for an entity'
    parameters:
      - name: index
        in: path
        required: true
        type: integer
        description: index of entity to lookup
    produces:
      - application/json
    responses:
      '200':
        description: links for an entity within the knowledge graph
    """
    global NET

    id = int(index)

    if id >= 0 and id < len(NET.id_list):
        result = NET.id_list[id]
    else:
        result = None

    return jsonify(result)


@CACHE.cached(timeout=3000)
@APP.route("/api/v1/stuff", methods=["POST"])
def api_post_stuff ():
    """
    post some stuff
    ---
    tags:
      - example
    description: 'post some stuff'
    parameters:
      - name: mcguffin
        in: formData
        required: true
        type: string
        description: some stuff
    produces:
      - application/json
    responses:
      '200':
        description: got your stuff just fine
      '400':
        description: bad request; is the `mcguffin` parameter correct?
    """

    mcguffin = request.form["mcguffin"]
    
    response = {
        "received": mcguffin
        }

    status = HTTPStatus.OK.value

    return jsonify(response), status


######################################################################
## main

def main (args):
    global NET

    elapsed_time = NET.load_network(Path(args.corpus))
    print("{:.2f} ms corpus parse time".format(elapsed_time))

    APP.run(host="0.0.0.0", port=args.port, debug=True)


if __name__ == "__main__":
    # parse the command line arguments, if any
    parser = argparse.ArgumentParser(
        description="Rich Context: server, API, UI"
        )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="web IP port"
        )

    parser.add_argument(
        "--corpus",
        type=str,
        default=DEFAULT_CORPUS,
        help="corpus file"
        )

    main(parser.parse_args())
