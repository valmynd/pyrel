# -*- coding: utf-8 -*-

import pstats, cProfile
from database import *
from models import Model

import sqlalchemy.sql
from sqlalchemy import MetaData, create_engine
engine = create_engine('postgresql://test:123456@localhost/test1', pool_size=5, max_overflow=-1)


# simple test
connection = engine.connect()
result = connection.execute("select * from film")
# databse introspection
#print(repr(Autor))
#s = sqlalchemy.sql.Select([Autor.c.nachname]).where(Autor.c.nachname.like("%us"))
#print(getattr(Autor.c.nachname, "like")("%us"))
#s = s.select_from(meta.tables["buch"])
connection.close()

"""create objects using sqlalchemy's reflection; attribute is what is returned by create_engine()"""
def introspect_sqlalchemy(engine):
	# fun: http://www.incurlybraces.com/convert-underscored-names-camel-case-python.html
	# may have a method that does just that, if someone wants it
	meta = MetaData()
	meta.reflect(bind=engine)
	newmodels_dict = {} # will be returned
	for table in meta.sorted_tables:
		newcolumns_dict = {} # will be used as parameter for type()
		for column_sqla in table.columns:
			# get the table related by a foreign key: list(employees.c.employee_dept.foreign_keys)[0].column.table
			#print c.name, c.unique, c.nullable, c.primary_key, c.foreign_keys
			## Adapt types
			coltype_name = column_sqla.type.__class__.__name__.lower()
			if "int" in coltype_name:
				columnclass = IntegerColumn
			elif "char" in coltype_name or coltype_name == "text":
				columnclass = TextColumn
			elif coltype_name == "boolean":
				columnclass = BooleanColumn
			elif coltype_name == "date":
				columnclass = DateColumn
			else: # TODO / raise NotImplementedError
				# decimal is exactly as precise as declared, while numeric is at least as precise as declared
				print "=========== not handled in introspect_sqlalchemy(): ", coltype_name
				columnclass = TextColumn
			columnobject = columnclass()
			## Adapt PrimaryKey/ForeinKey
			if column_sqla.primary_key:
				columnobject = PrimaryKey(columnobject)
			if column_sqla.foreign_keys:
				assert(len(column_sqla.foreign_keys) == 1) # wonder why every column stores a set() of foreign_keys in sqlalchemy??
				pkcol_sqla = column_sqla.foreign_keys.pop().column
				pkcol_pyrel = getattr(newmodels_dict[pkcol_sqla.table.name], pkcol_sqla.name)
				columnobject = ForeignKey(pkcol_pyrel)
			## Adapt further attributes
			columnobject.not_null(not column_sqla.nullable)
			columnobject.unique(column_sqla.unique)
			columnobject._sqla = column_sqla
			newcolumns_dict[column_sqla.name] = columnobject
		newmodel = type(str(table.name), (Model,), newcolumns_dict)
		newmodels_dict[table.name] = newmodel
		newmodel._sqla = table
	return newmodels_dict
models = introspect_sqlalchemy(engine)

def operator_to_sqlalchemy(expr):
	# use sqlalchemy equivalences
	left = expr._left_operand
	right = expr._right_operand
	if hasattr(left, "_sqla"):
		left = left._sqla
	if hasattr(right, "_sqla"):
		right = right._sqla
	# execute operator in sqlalchemy
	return getattr(left, expr._operator)(right)
#stmt = "saf" == models["buch"].titel
#print operator_to_sqlalchemy(stmt)

def command_to_string_sqlalchemy(cmd):
	# for this to work, we need
	#  * sqlalchemy equivalent for _Column
	#  * sqlalchemy equivalent for fromclause, whereclause
	where_clause = None
	if cmd.where_expr:
		where_clause = operator_to_sqlalchemy(cmd.where_expr)
	#assert(len(cmd.relevant_columns) > 0)
	stmt = sqlalchemy.sql.Select(
		columns = [rc._sqla for rc in cmd.relevant_columns],
		whereclause=where_clause,
		from_obj=None,
		distinct=False,
		having=None
	)
	return stmt
#stmt = select(models["film"]).where("saf" == models["film"].name)
#connection = engine.connect()
#stmt = command_to_string_sqlalchemy(stmt)
#result = connection.execute(stmt)
#print(str(stmt), result.fetchone())

class ModelTest(Model):
	z = TextColumn()
	x = TextColumn()

y = ModelTest(x=12)

print(y._columns)
print(repr(ModelTest.x))
print(list(y))

