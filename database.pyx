# encoding: utf-8
# cython: profile=True
# cython: language_level=3
__author__ = "C.Wilhelm"
__license__ = "AGPL v3"

#from cpython cimport bool
#cimport expressions
from copy import copy

cdef extern from "cescape.h":
	char* escape_html(char* bstr)
cpdef bytes escape(s):
	if isinstance(s, unicode):
		s = s.encode('UTF-8') # seems pretty fast: 0.20 vs 0.25 seconds
	cdef char *r = escape_html(s) # up to twice as fast as cgi.escape()
	if r == NULL:
		raise MemoryError("String too long")
	return r

OPERATOR_OR = b" or "
OPERATOR_AND = b" and "
OPERATOR_LT = b" < "
OPERATOR_LE = b" <= "
OPERATOR_GE = b" >= "
OPERATOR_GT = b" > "
OPERATOR_EQ = b" = "
OPERATOR_NE = b" != "

# _Operand shall contain all operators relevant for Column objects
cdef class _Operand:
	def __or__(self, other): # a | b
		# because the | operator has the highest operator precedence, the
		# operators need to be put into brackets, like this: i | (i < i)
		# thus you can also use i.__or__(i < i)
		return Expression(OPERATOR_OR, self, other)
	def __and__(self, other): # a & b
		# because the & operator has the highest operator precedence, the
		# operators need to be put into brackets, like this: i & (i < i)
		# thus you can also use i.__and__(i < i)
		return Expression(OPERATOR_AND, self, other)
	def __richcmp__(self, other, int operator):
		# http://docs.cython.org/src/userguide/special_methods.html#rich-comparisons
		""" # don't remove this, as it may get relevant in later versions of cython:
			def __lt__(self, other): # a < b
				return Expression(OPERATOR_LT, self, other)
			def __le__(self, other): # a <= b
				return Expression(OPERATOR_LE, self, other)
			def __ge__(self, other): # a >= b
				return Expression(OPERATOR_GE, self, other)
			def __gt__(self, other): # a > b
				return Expression(OPERATOR_GT, self, other)
			def __eq__(self, other): # a == b
				return Expression(OPERATOR_EQ, self, other)
			def __ne__(self, other): # a != b
				return Expression(OPERATOR_NE, self, other)"""
		if operator == 0: # < 0 lt # a < b
			op = OPERATOR_LT
		elif operator == 1: # <= 1 le # a <= b
			op = OPERATOR_LE
		elif operator == 2: # == 2 eq # a <= b
			op = OPERATOR_EQ
		elif operator == 3: # != 3 ne # a != b
			op = OPERATOR_NE
		elif operator == 4: # > 4 gt # a > b
			op = OPERATOR_GT
		elif operator == 5: # >= 5 ge # a >= b
			op = OPERATOR_GE
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
		return "%s%s%s" % (self._left_operand, self._operator, self._right_operand)

""" property-like Interface for Column objects, not visible from python """
cdef class _Column(_Operand):
	# readonly doesn't apply for cython-access
	cdef public _Column _reference # None if this is no ForeignKey
	cdef readonly unicode _name # assigned via late-binding
	cdef public object _sqla # may hold backend equivalent
	def __cinit__(self):
		pass#self._instantiation_count = xy
	def __get__(self, instance, owner):
		# see http://docs.python.org/reference/datamodel.html
		if instance is None:
			return owner
		return owner[self._instantiation_count]
	def __set__(self, instance, value):
		instance[self._instantiation_count] = value

cdef class TestColumn(_Column):
	def __str__(self):
		return "c"

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
				self.where_expr = other.where_expr
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
	def columns(self, *columns):
		# use this method to redefine relevant_columns after creation of Command object
		# force relevant_columns to concist of Column/Table/Aggregation objects
		# return relevant_columns if no parameters are given
		if columns:
			self.relevant_columns = [] # emptied before appending
			for col in columns:
				if hasattr(col, "_reference"):
					self.relevant_columns.append(col)
				elif hasattr(col, "relevant_columns"): # maybe move this to select.from_(), handling joins there
					self.relevant_columns += col._columns
				else: # TODO: Aggregations
					raise TypeError("As of yet, only Column- and Model objects are allowed in append_columns()")
			# TODO: fill involved_tables list
			return self.command_changed()
		return self.relevant_columns
	def command_changed(self):
		# must be called by every method that has an influence on the prepared statement,
		# or otherwise calling that method may have no effect at all!
		self.prepared_statement = ""
		return self
	# Subclasses shall implement: value(), __str__()

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