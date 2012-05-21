# -*- coding: utf-8 -*-

# writing metaclasses in cython led to segfaults
# TODO: try with newer versions of cython (last tried with 0.14.x)
__author__ = "C.Wilhelm"
__license__ = "AGPL v3"

from database import _Model

class ModelMeta(type):
	@classmethod
	def __prepare__(metacls, name, bases, **kwargs):
		return OrderedDict()
	def __init__(cls, name, bases, attrs):
		# on introspection, conclude fields / models with language-codes
		# all this currently doesn't work with cython cdef classes
		cls._name = attrs.pop("_name", name.lower())
		cls._sqla = attrs.pop("_sqla", name.lower())
		cls._columns = []
		i = 0
		for objname, obj in attrs.iteritems():
			if hasattr(obj, "_instantiation_count"):
				obj.bind_late(cls, unicode(objname), i)
				cls._columns.append(obj)
				i = i + 1
		type.__init__(cls, name, bases, attrs)
	def __repr__(self):
		return "<Model %s>" % (self._name)
	def __str__(self):
		return self._name

class Model(_Model): # (list, metaclass=ModelMeta):
	__metaclass__ = ModelMeta
	def __str__(self):
		return self._name
	@classmethod
	def get(cls, id):
		"""fetch one row in the name specified by it's primary key guaranteed to be cached
		shortcut to something like db.tb.select().where(db.tb._pk[0] == 2).fetch(cache=True).pop()
		id: value of primary-key column to query for, result will be one row as an object of the Model or None
		note that every call to get() will raise a seperate query to the database, SO DO NOT USE IN LOOPS"""
		if len(cls._primary_keys) != 1:
			raise Exception("you can use get() only for tables with one primary key column")
		# command-string is generated at central place once per connection: ModelMeta.bind_parent()
		#res = cls._database.query(cls._sql_each, (id,), namespace=cls._name)
		#if len(res) == 1:
		#	return cls(res.pop())
		return None
