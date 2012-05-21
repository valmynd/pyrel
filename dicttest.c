#include "dicttest.h"
/*
Iterate through dict
http://www.gilgalab.com.br/2011/05/03/python-c-api-first-step
http://docs.python.org/c-api/intro.html#reference-counts
*/

int test(const PyObject *dict) {
	PyObject *key, *value;
	Py_ssize_t pos = 0;
	while (PyDict_Next(dict, &pos, &key, &value)) {
		/* begin print attrs */
		char *keytype = (char*)key->ob_type->tp_name;
		char *valtype = (char*)value->ob_type->tp_name;
		PyObject *keystr = PyObject_Bytes(key); /* equivalent to str(o) in python */
		PyObject *valstr = PyObject_Bytes(value); /* may call o.__str__() */
		/* the returned pointer of PyBytes_AsString(o) refers to the internal buffer of o, not a copy. The data must not be modified in any way,
			it must not be deallocated: http://docs.python.org/release/3.0.1/c-api/bytes.html#PyBytes_AsString */
		printf("Key Type: %s Key String: %s - Value Type: %s Value String: %s\n", keytype, PyBytes_AsString(keystr), valtype, PyBytes_AsString(valstr));
		Py_DECREF(keystr);
		Py_DECREF(valstr);
		/* end print attrs */
	}
	return 0;
}

/*
int test_old1(PyObject *dict) {
	PyObject *key, *value;
	Py_ssize_t pos = 0;
	while (PyDict_Next(dict, &pos, &key, &value)) {
		int i = PyInt_AS_LONG(value) + 1;
		PyObject *o = PyInt_FromLong(i);
		if (o == NULL)
			return -1;
		if (PyDict_SetItem(dict, key, o) < 0) {
			Py_DECREF(o);
			return -1;
		}
		Py_DECREF(o);
	}
	return 0;
}
*/
