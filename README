__license__ = "AGPL v3"

Plan
====
- 2 backends: native implementation and sqlalchemy-core (has many backends, connectionpool, reflection etc)
- use alembic for alter table statements (based on sqlalchemy, http://alembic.readthedocs.org)
- integrate searchengine, e.g. SphinxQL
- advantage over sqlalchemy-core:
	* one can convert command-objects into each other, useful for generating webforms
	* syntax is closer to sql, e.g. select().from_(Model).where((Model.x == 2) & (Model.y ==3))
	* minimalist approach with broader focus than ORM (e.g. somecolumn.op('&')(0xff) would not work with native backend)
	* advantage over pure object databases:
	* querying more convenient due to SQL-like syntax
