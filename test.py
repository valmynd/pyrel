# -*- coding: utf-8 -*-

import pstats, cProfile
from database import *

i = TestColumn()
#print i | (i < i) == i
#print i.__and__(i < i) == i

x = select()
y = update(x)
y.values("saf", "sf")
z = delete(y)


model = TestColumn()
stmt = select().from_(model).where((model == 2) & (model ==3))
expr = (model == 2) & (model ==3)

import sqlalchemy.sql
def operator_to_sqlalchemy(op, left, right):
	# use sqlalchemy equivalences
	if hasattr(left, "_sqla"):
		left = left._sqla
	if hasattr(right, "_sqla"):
		right = left._sqla
	# redo operator handling
	if op == OPERATOR_OR:
		return left.__or__(right)
	"""
	if op == OPERATOR_AND = b" and "
	if op == OPERATOR_LT = b" < "
	if op == OPERATOR_LE = b" <= "
	if op == OPERATOR_GE = b" >= "
	if op == OPERATOR_GT = b" > "
	if op == OPERATOR_EQ = b" = "
	if op == OPERATOR_NE = b" != "
	"""

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

command_to_string_sqlalchemy(stmt)

"""
from collections import OrderedDict

class ModelMeta(type):
	@classmethod
	def __prepare__(metacls, name, bases, **kwargs):
		return OrderedDict()
	def __new__(cls, name, bases, classdict):
		result = type.__new__(cls, name, bases, dict(classdict))
		result._members = tuple(classdict)
		return result

class Model(metaclass=ModelMeta):
	def one(self): pass
	def two(self): pass
	def three(self): pass
	def four(self): pass

print(Model._members)
"""
