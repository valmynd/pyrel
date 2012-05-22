# encoding: utf-8
# cython: profile=True
# cython: language_level=3
__author__ = "C.Wilhelm"
__license__ = "AGPL v3"
# read this: http://effbot.org/zone/simple-top-down-parsing.htm
# http://docs.sqlalchemy.org/en/latest/core/schema.html#reflecting-all-tables-at-once
# follow this: http://www.google-melange.com/gsoc/project/google/gsoc2012/redbrain1123/28002
from cpython cimport bool
from cpython cimport PyList_New, PyList_SET_ITEM
#cdef extern from "object.h":
#	ctypedef class __builtin__.type [object PyHeapTypeObject]:
#		pass

cdef extern from "cescape.h":
	char* escape_html(char*)
cpdef bytes escape(s):
	if isinstance(s, unicode):
		s = s.encode('UTF-8') # seems pretty fast: 0.20 vs 0.25 seconds
	cdef char *r = escape_html(s) # up to twice as fast as cgi.escape()
	if r == NULL:
		raise MemoryError("String too long")
	return r

# testing extensions
#cdef extern from "dicttest.h":
#	int test(dict)
#cpdef test_test(dict x):
#	test(x)

opstring_mapping = { "__and__" : " and ", "__or__" : " or ",  "__lt__" : " < ", "__le__" : " <= ", "__ge__" : " >= ", "__ge__" : " > ", "__eq__" : " = ", "__ne__" : " != " }

# _Operand shall contain all operators relevant for Column objects
cdef class _Operand:
	def __or__(self, other): # a | b
		# because the | operator has the highest operator precedence, the
		# operators need to be put into brackets, like this: i | (i < i)
		# thus you can also use i.__or__(i < i)
		return Expression("__or__", self, other)
	def __and__(self, other): # a & b
		# because the & operator has the highest operator precedence, the
		# operators need to be put into brackets, like this: i & (i < i)
		# thus you can also use i.__and__(i < i)
		return Expression("__and__", self, other)
	def __richcmp__(self, other, int operator):
		# http://docs.cython.org/src/userguide/special_methods.html#rich-comparisons
		if operator == 0: # < 0 lt # a < b
			op = "__lt__"
		elif operator == 1: # <= 1 le # a <= b
			op = "__le__"
		elif operator == 2: # == 2 eq # a <= b
			op = "__eq__"
		elif operator == 3: # != 3 ne # a != b
			op = "__ne__"
		elif operator == 4: # > 4 gt # a > b
			op = "__gt__"
		elif operator == 5: # >= 5 ge # a >= b
			op = "__ge__"
		return Expression(op, self, other)

cdef class Expression(_Operand):
	cdef public object _operator
	cdef public object _left_operand
	cdef public object _right_operand
	def __init__(self, t, left_operand, right_operand):
		self._operator = t
		self._left_operand = left_operand
		self._right_operand = right_operand
	def __str__(self):
		#if isinstance(self._right_operand, _Operand):
		#print (self._left_operand.__class__.__name__, self._right_operand.__class__.__name__)
		return "%s%s%s" % (self._left_operand, opstring_mapping[self._operator], self._right_operand)

# _Model is a Baseclass for Model (can't apply Metaclass within Cython classes, yet)
cdef class _Model(list):
	def __init__(self, *args, **kwargs):
		"""this constructor is meant to be called in order to create per-row objects
		tuples can be converted into Model objects just like this: Model(*result.fetchone())
		when creating Model objects manually, this syntax might be preferred: Model(col="afs")
		you can't mix those, e.g. Model("asf", "saf", x="saf") won't work"""
		if args: # fast, but there are some rules -> set __debug__ = False when benchmarking
			assert(not kwargs)
			assert(len(args) == len(self._columns))
			list.__init__(self, args)
			return
		# if not all attributes are set, assign default values
		cdef int i = 0
		cdef list L = <list> PyList_New(len(self._columns)) # avoid reallocation this way
		for c in self._columns:
			# PyList_SET_ITEM is used to fill in new lists where there is no previous content
			PyList_SET_ITEM(L, i, kwargs.pop(c._name, c.default()))
			i = i+1
		list.__init__(self, L)
	# operators for Model Objects (Aggregations, Joins?)
	def sum(self):
		return Expression("__sum__", self, None)
	def min(self):
		return Expression("__min__", self, None)
	def avg(self):
		return Expression("__avg_", self, None)
	#def count(self, distinct = False):
	#	return Expression("__count__", self, None)

cdef class Database:
	# readonly doesn't apply for cython-access
	cdef readonly unicode _name
	cdef readonly list _models # see models()
	cdef readonly _user_model # required for versioning, permissions
	def __cinit__(self):
		self._name = "UNASSIGNED"
		self._models = []
		self._user_model = None
	def __init__(self):
		#self._cache = cacheobj or NullCache()
		# TODO: warn at the beginning, that authorization is disabled and a usermodel should be picked to fix that
		# _user_model should point to something that implements UserModel, required for versioning, permissions
		pass
	def bind_models(self, *model_args):
		# use this method to redefine _models after creation of Database object
		# force _models to concist of valid Model objects
		# return _models if no parameters are given
		for m in model_args:
			assert(hasattr(m, "_columns"))
			m.bind_parent(self) # will call self._models.append(m)
		return self
	def user_model(self, model = None):
		if model is not None:
			assert(hasattr(model, "_columns"))
			self._user_model = model
			return self
		return self._user_model
		

# note on _Command: think of it as prepared statement
# only the way things are stored should be optimized
cdef class _Command:
	## attributes that don't need to be copied:
	# prepared_statement: need to be regenerated if anything changed (see command_changed)
	cdef public unicode prepared_statement
	# general attributes for common queries:
	#  all subclasses need to be able to be converted into each other
	#  back and forth, so any information must be avaiable, even if
	#  irrelevant for current operation
	## attributes that need to be copied
	cdef readonly list relevant_columns # idea: only store names, have a method to forward to getattr(parent, colname)
	cdef readonly list groupby_columns
	cdef readonly list orderby_columns
	cdef readonly list involved_tables
	cdef public list values_commit
	cdef public list values_where
	cdef public list values_having
	cdef readonly Expression where_expr
	cdef readonly Expression having_expr
	cdef readonly int offset_num
	cdef readonly int limit_num
	def __cinit__(self):
		# http://docs.cython.org/src/reference/extension_types.html#initialization-cinit-and-init
		# All C-level attributes have been initialized to 0 or null
		# Python have been initialized to None, but you can not rely on that
		self.prepared_statement = "" # empty means, it needs to be (re)generated
		self.relevant_columns = []
		self.groupby_columns = []
		self.orderby_columns = []
		self.involved_tables = []
		self.values_commit = []
		self.values_where = []
		self.values_having = []
		self.where_expr = None
		self.having_expr = None
		self.offset_num = -1
		self.limit_num = -1
	def __init__(self, *relevant_columns):
		# this is a conversion constructor, e.g. Select(Update()) should work
		if len(relevant_columns) == 1:
			other = relevant_columns[0]
			if hasattr(other, "relevant_columns"):
				# KEEP THIS UP TO DATE! (e.g. 11 attributes -> 11 copy instructions)
				# TODO: make shure, that shallow copies are made
				self.relevant_columns = other.relevant_columns[:]
				self.groupby_columns = other.groupby_columns[:]
				self.orderby_columns = other.orderby_columns[:]
				self.involved_tables = other.involved_tables[:]
				self.values_commit = other.values_commit[:]
				self.values_where = other.values_where[:]
				self.values_having = other.values_having[:]
				self.where_expr = other.where_expr # evtl: deep-copy needed, e.g. if values change?
				self.having_expr = other.having_expr
				self.offset_num = other.offset_num
				self.limit_num = other.limit_num
				return
		elif relevant_columns: # may intentionally be left empty
			self.columns(*relevant_columns) # e.g. stmt = select().from_(model)
	def __str__(self):
		# __str__ methods prepare SQL command strings for query_*()
		# maybe forward this to libgda/odb++ or anything
		return ""#raise NotImplementedError
	def where(self, expr):
		if self.where_expr is None:
			self.where_expr = expr
			return self.command_changed()
		self.where_expr.__and__(expr)
		return self.command_changed()
	def columns(self, *column_args):
		# use this method to redefine relevant_columns after creation of Command object
		# force relevant_columns to concist of Column/Table/Aggregation objects
		# return relevant_columns if no parameters are given
		if column_args:
			self.relevant_columns = [] # emptied before appending
			for col in column_args:
				print ("AIHS")
				if hasattr(col, "_instantiation_count"): # is _Column
					self.relevant_columns.append(col)
				elif hasattr(col, "_columns"): # maybe move this to select.from_(), handling joins there
					self.relevant_columns += col._columns
				else: # TODO: Aggregations
					raise TypeError("As of yet, only Column- and Model objects are allowed in append_columns()")
			return self.command_changed() # TODO: fill involved_tables list
		return self.relevant_columns
	def command_changed(self):
		# must be called by every method that has an influence on the prepared statement,
		# or otherwise calling that method may have no effect at all!
		self.prepared_statement = ""
		return self
	# Subclasses shall implement: values(), __str__()

cdef class delete(_Command):
	#def __init__(self, _Command other): # DOES NOT WORK, MAYBE FIXED IN LATER CYTHON
	#	_Command.__init__(other)
	def values(self):
		# make variants to return other values, depending on command type
		return self.values_where

cdef class update(_Command):
	def values(self, *values_commited):
		if values_commited:
			self.values_commit = list(values_commited) # replaces them!
			return self
		return self.values_commit + self.values_where # ensure the right order

cdef class insert(_Command):
	def values(self, *values_commited):
		if values_commited:
			self.values_commit = list(values_commited) # replaces them!
			return self
		return self.values_commit # there is no where clause for insert()

cdef class select(_Command):
	def from_(self, *models):
		return self.columns(*models)
	def values(self):
		return self.values_where + self.values_having
	def groupby(self, *columns):
		self.groupby_columns = list(columns)
		return self.command_changed()
	def having(self, expr):
		if self.having_expr is None:
			self.having_expr = expr
			return self.command_changed()
		self.having_expr.__and__(expr)
		return self.command_changed()
	def limit(self, val = None):
		self.limit_num = val
		return self.command_changed()
	def offset(self, val = None):
		self.offset_num = val
		return self.command_changed()

""" property-like Interface for Column objects, not visible from python """
cdef class _Column(_Operand):
	# readonly doesn't apply for cython-access
	cdef readonly unicode _name # assigned via late-binding
	cdef readonly object _model # assigned via late-binding
	cdef readonly int _instantiation_count # assigned via late-binding
	cdef public object _sqla # may hold backend equivalent
	cdef public object _default # default value to fallback to
	cdef public bool _nullable # set via not_null()
	cdef public bool _unique # set via unique()
	cdef public _Column _representative # set via representative()
	def __cinit__(self):
		self._instantiation_count = -1
		self._name = "UNASSIGNED"
		self._model = None
		self._default = None
		self._nullable = True
	def __get__(self, instance, owner):
		# see http://docs.python.org/reference/datamodel.html
		if instance is None:
			return self
		return instance[self._instantiation_count]
	def __set__(self, instance, value):
		instance[self._instantiation_count] = value
	def bind_parent(self, object parent, unicode name, int list_position):
		"""assign a Model object to the column and a name for itself, this usually happens automatically"""
		self._model = parent
		self._name = name
		self._instantiation_count = list_position
		return self
	def default(self, value = None):
		# may want to raise Exception if this column is NOT NULL
		if value is not None:
			self._default = value
			return self
		#if self._default is None and not self._nullable: # FIXME: will complain for primary keys!
		#	raise Exception("There is no default Value for %s" % self._name)
		return self._default
	def not_null(self, not_null = True):
		self._nullable = not not_null
		return self
	def unique(self, unique = True):
		if unique:
			print("==== unique spotted:", self)
		self._unique = unique
		return self
	def representative(self, representative = True):
		"""set whether this column shall be used to represent the object, e.g. in a ComboBox"""
		self._representative = representative
		return self
	def __str__(self):
		return self._name
	def __repr__(self):
		return "<%s %s.%s>" % (self.__class__.__name__, self._model._name, self._name)

cdef class TextColumn(_Column):
	pass
cdef class BooleanColumn(_Column):
	pass
cdef class IntegerColumn(_Column):
	pass
cdef class FloatColumn(_Column):
	pass
cdef class DecimalColumn(_Column):
	pass
cdef class DateColumn(_Column):
	pass
cdef class TimeColumn(_Column):
	pass
cdef class DatetimeColumn(_Column):
	pass
cdef class PrimaryKey(_Column):
	pass
cdef class ForeignKey(_Column):
	cdef readonly _Column _reference
	cdef readonly unicode _reference_on_delete
	def __init__(self, reference, on_delete = "cascade"):
		_Column.__init__(self)
		# reference: either the referenced Model or it's primary-key-object (will be the latter afterwards)
		self._reference_on_delete = on_delete.lower() # cascade, delete, set null, set default
		self._reference = reference # will contain the pk-column of the referenced table, handled via finalize()
		#self._refsamenames = False # handled in finalize()
		#self._choices = None
		#self._renderclass = ComboBox
	def __repr__(self):
		rstr = _Column.__repr__(self)
		return rstr.replace(">", " references %s>" % str(self._reference))
