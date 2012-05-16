# -*- coding: utf-8 -*-

# writing metaclasses in cython led to segfaults
# TODO: try with newer versions of cython (last tried with 0.14.x)
__author__ = "C.Wilhelm"
__license__ = "AGPL v3"


#j2ee spring struts jaxb 10h/woche für 8.56€/h = 372€/M
#Praktikum im Umfang von 30 ECTS; 3SHK; 1.6
# christoph.jobst@studserv.uni-leipzig.de
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

class Model(list): # (list, metaclass=ModelMeta):
	__metaclass__ = ModelMeta
	def __init__(self, *args, **kwargs):
		"""this constructor is meant to be called in order to create per-row objects
		tuples can be converted into Model objects just like this: Model(*result.fetchone())
		when creating Model objects are created manually, this syntax might be preferred: Model(col="afs")
		you can't mix those, e.g. Model("asf", "saf", x="saf") won't work"""
		if args: # fast, but there are some rules -> set __debug__ = False when benchmarking
			assert(len(kwargs) == 0)
			assert(len(args) == len(self._columns))
			list.__init__(self, args)
			return
		# if not all attributes are set, assign default values
		#tmp = [0]*len(self._columns) # initial size
		list.__init__(self, [kwargs.pop(c._name, c.default()) for c in self._columns])
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
