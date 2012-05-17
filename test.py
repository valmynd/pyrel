# -*- coding: utf-8 -*-

import pstats, cProfile
from database import *
from models import Model


import sqlalchemy.sql
from sqlalchemy import MetaData, create_engine
engine = create_engine('postgresql://test:123456@localhost/test1', pool_size=5, max_overflow=-1)

'''
# simple test
connection = engine.connect()
result = connection.execute("select * from autor")
# databse introspection

#print(meta.tables.keys())

Autor = meta.tables["autor"]
#print(repr(Autor))
s = sqlalchemy.sql.Select([Autor.c.nachname]).where(Autor.c.nachname.like("%us"))
print(getattr(Autor.c.nachname, "like")("%us"))
#s = s.select_from(meta.tables["buch"])
result = connection.execute(s)
print(str(s), result.fetchone())
connection.close()
'''
"""create objects using sqlalchemy's reflection; attribute is what is returned by create_engine()"""
def introspect_sqlalchemy(engine):
	meta = MetaData()
	meta.reflect(bind=engine)
	newmodels_dict = {} # will be returned
	for table in meta.sorted_tables:
		newcolumns_dict = {} # will be used as parameter for type()
		for c in table.columns:
			# get the table related by a foreign key: list(employees.c.employee_dept.foreign_keys)[0].column.table
			#print c.name, c.nullable, c.primary_key, c.foreign_keys
			## Adapt types
			coltype_name = c.type.__class__.__name__.lower()
			if "int" in coltype_name:
				columnclass = IntegerColumn
			elif "char" in coltype_name or "string" in coltype_name or "unicode" in coltype_name:
				columnclass = TextColumn
			else: # TODO / raise NotImplementedError
				# decimal is exactly as precise as declared, while numeric is at least as precise as declared
				print "=========== not handled in introspect_sqlalchemy(): ", coltype_name
				columnclass = TextColumn
			columnobject = columnclass().not_null(not c.nullable)
			## Adapt PrimaryKey/ForeinKey
			if c.primary_key:
				columnobject = PrimaryKey(columnobject)
			if c.foreign_keys:
				assert(len(c.foreign_keys) == 1)
				pkcol = c.foreign_keys.pop().column
				print getattr(newmodels_dict[pkcol.table.name], pkcol.name)
			newcolumns_dict[c.name] = columnobject
		newmodel = type(str(table.name), (Model,), newcolumns_dict)
		newmodels_dict[table.name] = newmodel
	return newmodels_dict
introspect_sqlalchemy(engine)

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
'''

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
'''

class ModelTest(Model):
	z = TextColumn()
	x = TextColumn()
print ("asf")

y = ModelTest(x=12)

print(y._columns)
print(str(y))
