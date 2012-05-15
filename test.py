# -*- coding: utf-8 -*-

import pstats, cProfile
from database import *
from models import Model

i = TextColumn()
#print i | (i < i) == i
#print i.__and__(i < i) == i

x = select()
y = update(x)
y.values("saf", "sf")
z = delete(y)


model = TextColumn()
stmt = select().from_(model).where((model == 2) & (model ==3))
expr = (model == 2) & (model ==3)

import sqlalchemy.sql
from sqlalchemy import MetaData, create_engine
engine = create_engine('postgresql://test:123456@localhost/test1', pool_size=5, max_overflow=-1)

# simple test
connection = engine.connect()
result = connection.execute("select * from autor")
# databse introspection
meta = MetaData()
meta.reflect(bind=engine)
#print(meta.tables.keys())

Autor = meta.tables["autor"]
#print(repr(Autor))
s = sqlalchemy.sql.Select([Autor.c.nachname]).where(Autor.c.nachname.like("%us"))
print(getattr(Autor.c.nachname, "like")("%us"))
#s = s.select_from(meta.tables["buch"])
result = connection.execute(s)
print(str(s), result.fetchone())
connection.close()

def command_to_string_sqlalchemy(cmd):
	# for this to work, we need
	#  * sqlalchemy equivalent for _Column
	#  * sqlalchemy equivalent for fromclause, whereclause
	if cmd.where_expr:
		# need mapping, e.g. m[OPERATOR_GE] to return "__ge__"
		print cmd.where_expr
	stmt = sqlalchemy.sql.Select(
		columns = [],
		whereclause=None,
		from_obj=None,
		distinct=False,
		having=None
	)

def operator_to_sqlalchemy(op, left, right):
	# use sqlalchemy equivalences
	if hasattr(left, "_sqla"):
		left = left._sqla
	if hasattr(right, "_sqla"):
		right = left._sqla
	# redo operator handling
	if op == OPERATOR_OR:
		return left.__or__(right)

#command_to_string_sqlalchemy(stmt)

class ModelTest(Model):
	z = TextColumn()
	x = TextColumn()
print ("asf")

y = ModelTest(x=12)

print(y._columns)
print(str(y))
