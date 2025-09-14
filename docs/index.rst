Deimos Router Documentation
===========================

Deimos Router is a powerful and flexible routing system for Large Language Model (LLM) API calls. It allows you to intelligently route requests to different models based on customizable rules, enabling you to optimize for cost, performance, and capability.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting-started
   user-guide
   rule-types
   examples
   api-reference

Key Features
------------

* **Intelligent Routing**: Route LLM requests based on content, task type, message length, conversation context, and more
* **Rule Composition**: Chain multiple rules together for complex routing logic
* **Multiple Rule Types**: Built-in support for task-based, code detection, language detection, and other routing strategies
* **OpenAI Compatible**: Drop-in replacement for OpenAI API calls with routing capabilities
* **Extensible**: Easy to create custom rules for your specific use cases

Quick Start
-----------

Install Deimos Router:

.. code-block:: bash

   pip install deimos-router

Basic usage:

.. code-block:: python

   from deimos_router import Router, register_router, chat
   from deimos_router.rules import TaskRule

   # Create a router with task-based routing
   router = Router(
       name="my-router",
       rules=[
           TaskRule(
               name="task-router",
               triggers={
                   'coding': 'openai/gpt-4o',
                   'creative': 'openai/gpt-4o',
                   'simple': 'openai/gpt-4o-mini'
               }
           )
       ],
       default_model="openai/gpt-4o-mini"
   )
   
   register_router(router)
   
   # Use the router for chat completions
   response = chat.completions.create(
       model="deimos/my-router",
       messages=[{"role": "user", "content": "Help me write Python code"}],
       task="coding"
   )

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`