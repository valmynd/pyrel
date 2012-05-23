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
		cls._sqla = attrs.pop("_sqla", None) # maybe do some backend introspection
		cls._database = attrs.pop("_database", None) # fixme: call bind_parent
		cls._columns = []
		i = 0
		for objname, obj in attrs.iteritems():
			if hasattr(obj, "_instantiation_count"):
				obj.bind_parent(cls, unicode(objname), i)
				cls._columns.append(obj)
				i = i + 1
		type.__init__(cls, name, bases, attrs)
	def bind_parent(cls, parent):
		# called from within Database.sync(), Database.bind_models()
		cls._database = parent
		# add itself to _tables and _table_names
		parent._models.append(cls)
		# make it accessible as an attribute => won't work, as Database is a cdef class
		#setattr(parent, cls._name, cls)
		# TODO: prepare sql_each and sql_populate
		#if len(cls._translated) > 0:# TODO: same behaviour in introspect
		return cls
	def __repr__(self):
		return "<Model %s>" % (self._name)
	def __str__(self):
		return self._name

class Model(_Model): # (list, metaclass=ModelMeta):
	__metaclass__ = ModelMeta
	def __str__(self):
		return self._name
	#@classmethod
	#def new(cls, name, *column_objects):
	# need an alternative way not using metaclass,thus preferred way to spawn new models in cython
	# problem: distinguishing between model class (e.g. table) and model object (e.g. row)
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


	'''# operators for Model Objects (Aggregations, Joins?)
	def sum(self):
		return Expression("__sum__", self, None)
	def min(self):
		return Expression("__min__", self, None)
	def avg(self):
		return Expression("__avg_", self, None)
	#def count(self, distinct = False):
	#	return Expression("__count__", self, None)'''
