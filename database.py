# encoding: utf-8
# cython: profile=True
# cython: language_level=3
__author__ = "C.Wilhelm"
__license__ = "AGPL v3"
# follow this: http://www.google-melange.com/gsoc/project/google/gsoc2012/redbrain1123/28002
# maybe easier accomplished by doing this: http://docs.cython.org/src/tutorial/pure.html
# returns decorator in cython 0.17: https://sage.math.washington.edu:8091/hudson/job/cython-docs/doclinks/1/src/tutorial/pure.html
# need to be very diligent for optimization to work out: http://stackoverflow.com/questions/10394660/very-slow-cython-classes
#from cpython cimport bool
#cdef extern from "object.h":
#	ctypedef class __builtin__.type [object PyHeapTypeObject]:
#		pass
import cython

'''
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
'''

opstring_mapping = { "__and__" : " and ", "__or__" : " or ",  "__lt__" : " < ", "__le__" : " <= ", "__ge__" : " >= ", "__ge__" : " > ", "__eq__" : " = ", "__ne__" : " != " }

# _Operand shall contain all operators relevant for Column objects
@cython.cclass
class _Operand:
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
	'''def __richcmp__(self, other, operator):
		# http://docs.cython.org/src/userguide/special_methods.html#rich-comparisons
		# SEVERE missing feature in cython: http://trac.cython.org/cython_trac/ticket/130
		# cython.declare(cython.int) # http://groups.google.com/group/cython-users/browse_thread/thread/dab58913ae0deefd
		operator =
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
		return Expression(op, self, other)'''

@cython.cclass
class Expression(_Operand):
	_operator = cython.declare(object)
	_left_operand = cython.declare(object)
	_right_operand = cython.declare(object)
	def __init__(self, t, left_operand, right_operand):
		self._operator = t
		self._left_operand = left_operand
		self._right_operand = right_operand
	def __str__(self):
		#if isinstance(self._right_operand, _Operand):
		#print (self._left_operand.__class__.__name__, self._right_operand.__class__.__name__)
		return "%s%s%s" % (self._left_operand, opstring_mapping[self._operator], self._right_operand)

@cython.cclass
class Database:
	# readonly doesn't apply for cython-access
	_name = cython.declare(unicode) #typedef...
	_models = cython.declare(list) # see models()
	_user_model = cython.declare(object) # required for versioning, permissions
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
	def __getattr__(self, name):
		# if the attribute is found through the "normal" mechanism, __getattr__() is not called!
		if name[0] == "_":
			print(name)
		return name
	def __setattr__(self, name, val):
		pass

# note on _Command: think of it as prepared statement
# only the way things are stored should be optimized
@cython.cclass
class _Command:
	## attributes that don't need to be copied:
	# _prepared_statement: need to be regenerated if anything changed (see command_changed)
	_prepared_statement = cython.declare(unicode) #typedef...
	# general attributes for common queries:
	#  all subclasses need to be able to be converted into each other
	#  back and forth, so any information must be avaiable, even if
	#  irrelevant for current operation
	## attributes that need to be copied
	relevant_columns = cython.declare(list) # idea: only store names, have a method to forward to getattr(parent, colname)
	groupby_columns = cython.declare(list)
	orderby_columns = cython.declare(list)
	involved_tables = cython.declare(list)
	values_commit = cython.declare(list)
	values_where = cython.declare(list)
	values_having = cython.declare(list)
	where_expr = cython.declare(Expression)
	having_expr = cython.declare(Expression)
	offset_num = cython.declare(cython.int)
	limit_num = cython.declare(cython.int)
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
		elif not cython.compiled:
			self.__cinit__()
		if relevant_columns: # may intentionally be left empty
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
		self._prepared_statement = ""
		return self
	# Subclasses shall implement: values(), __str__()

@cython.cclass
class delete(_Command):
	#def __init__(self, _Command other): # DOES NOT WORK, MAYBE FIXED IN LATER CYTHON
	#	_Command.__init__(other)
	def values(self):
		# make variants to return other values, depending on command type
		return self.values_where

@cython.cclass
class update(_Command):
	def values(self, *values_commited):
		if values_commited:
			self.values_commit = list(values_commited) # replaces them!
			return self
		return self.values_commit + self.values_where # ensure the right order

@cython.cclass
class insert(_Command):
	def values(self, *values_commited):
		if values_commited:
			self.values_commit = list(values_commited) # replaces them!
			return self
		return self.values_commit # there is no where clause for insert()

@cython.cclass
class select(_Command):
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
@cython.cclass
class _Column(_Operand):
	# readonly doesn't apply for cython-access
	_name = cython.declare(unicode)
	_model = cython.declare(object) # assigned via late-binding
	_instantiation_count = cython.declare(cython.int) # assigned via late-binding
	_sqla = cython.declare(object) # may hold backend equivalent
	_default = cython.declare(object) # default value to fallback to
	_nullable = cython.declare(cython.bint) # set via not_null()
	_unique = cython.declare(cython.bint) # set via unique()
	_representative = cython.declare(cython.bint) # set via representative()
	def __cinit__(self): # need to initialize EVERY attribute if in pure-python mode
		self._name = "UNASSIGNED"
		self._instantiation_count = -1
		self._model = None
		self._sqla = None
		self._default = None
		self._nullable = True
		self._unique = False
		self._representative = False
	def __init__(self):
		if not cython.compiled:
			self.__cinit__()
	def __get__(self, instance, owner):
		# see http://docs.python.org/reference/datamodel.html
		if instance is None:
			return self
		return instance[self._instantiation_count]
	def __set__(self, instance, value):
		instance[self._instantiation_count] = value
	#@cython.locals(parent=Model, name=unicode, list_position=cython.int)
	def bind_parent(self, parent, name, list_position):
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
	#def __repr__(self):
	#	return "<%s %s.%s>" % (self.__class__.__name__, self._model._name, self._name)
#@cython.cclass # FIXME: DOESN'T WORK
class TextColumn(_Column):
	pass
#@cython.cclass
class BooleanColumn(_Column):
	pass
#@cython.cclass
class IntegerColumn(_Column):
	pass
#@cython.cclass
class FloatColumn(_Column):
	pass
#@cython.cclass
class DecimalColumn(_Column):
	pass
#@cython.cclass
class DateColumn(_Column):
	pass
#@cython.cclass
class TimeColumn(_Column):
	pass
#@cython.cclass
class DatetimeColumn(_Column):
	pass
#@cython.cclass
class PrimaryKey(_Column):
	def __init__(self, column = IntegerColumn, autoinc = True):
		""" column: (class or object) will be converted into PrimaryKey object
			autoinc: whether to AutoIncrement, will only an effect on IntegerColumn Objects"""
		#BaseColumn.__init__(self)
		#if isclass(column):
		#	column = column()
		#self.__dict__ = column.__dict__ # FIXME!!!
		#self._is_pk = True
		#self._autoincrement = autoinc # has only an effect on IntegerColumn
		# policy: in case of update: hiddenfield, in case of insert: NOT RENDERED (TODO: Nullrender_as)
		# thought for inserts: shall not every HiddenField be ignored in iserts? note there is readonly(for updates), too!
		#self._renderclass = HiddenField
		#self._choices = []
#@cython.cclass
class ForeignKey(_Column):
	_reference = cython.declare(object)
	_reference_on_delete = cython.declare(unicode)
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

@cython.cclass
class _Model(list): # (can't apply Metaclass within Cython classes, yet)
	def __init__(self, *args, **kwargs):
		"""tuple/lists can be converted into namedlist objects just like this:
		>>> seqobj = [1,2,3]
		>>> namedlist(*seqobj)
		when creating namedlist objects manually, this syntax might be preferred:
		>>> namedlist(attr1="afs")
		you can't mix those, e.g. namedlist("asf", "saf", x="saf") won't work"""
		if args: # fast, but there are some rules -> set __debug__ = False when benchmarking
			assert(not kwargs)
			assert(len(args) == len(self._columns))
			list.__init__(self, args)
			return
		# if not all attributes are set, assign default values
		L = cython.declare(list)
		L = [kwargs.pop(c._name, c.default()) for c in self._columns]
		'''cdef int i = 0
		cdef list L = <list> PyList_New(len(self._columns)) # avoid reallocation this way
		for c in self._columns:
			# PyList_SET_ITEM is used to fill in new lists where there is no previous content
			PyList_SET_ITEM(L, i, kwargs.pop(c._name, c.default()))
			i = i+1'''
		list.__init__(self, L)
