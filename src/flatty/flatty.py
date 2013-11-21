"""
This module provides the base layer for all generic flattening schemas.
With this classes - if not yet exists as a flatty module - 
you can easily write a module to support flatty schemas with your favorite
marshaller/unmarshaller. As an example look at the other modules eg. flatty.couchdb 

=======
Classes
=======
"""
import inspect
import datetime
import types
import sys


class MetaBaseFlattyType(type):
	def __eq__(self, other):
		""" 
		We need to overwrite this since the dynamically generated classes
		with ftype don't return equal when compared unlass compared only by names
		"""
		if hasattr(self, '__name__') and hasattr(other, '__name__') and \
			self.__name__ == other.__name__:
			return True
		else:
			return False
		
	def __instancecheck__(self, inst):
		""" 
		We also need to overwrite this because of the failing comparrission
		due to dynamic class generation
		"""
		candidates = [type(inst), inst.__class__] 
		issubclasslist = []
		for c in candidates:
			issubclasslist.append(self.__subclasscheck__(c))
		return any(issubclasslist)
	
	def __subclasscheck__(cls, sub):
		"""Implement issubclass(sub, cls)."""
		candidates = cls.__dict__.get("__subclass__", []) or [cls]
		str_candidates = []
		for c in candidates:
			str_candidates.append(str(c))
		
		str_c = []
		for c in sub.mro():
			str_c.append(str(c))
		
		intersect = set(str_c).intersection( set(str_candidates) )
		if len(intersect) > 0: return True
	

class BaseFlattyType(object):
	"""
	This class is the base Class for all special flatty schema types.
	These are :class:`TypedList` and :class:`TypedDict`
	"""
	
	ftype=None
	__metaclass__ = MetaBaseFlattyType
	
	
	
	@classmethod
	def set_type(cls, ftype):
		"""
		sets the type for the inherited flatty schema class
	
		Args:
			ftype: the type/class of the instance objects in the schema
			
		Returns:
			a class object with the class variable `ftype` set, used to 
			determine the instance type during unflattening
		"""
			
		# class must be generated dynamically otherwise ftype is set on
		# all classes which caused Bug #2
		new_cls = type(cls.__name__, cls.__bases__, dict(ftype=ftype, set_type=cls.set_type))
		setattr(sys.modules[cls.__module__], cls.__name__, new_cls)
		setattr(sys.modules[__name__], cls.__name__, None)
		new_cls.__module__ = cls.__module__
		return new_cls
	

class TypedList(BaseFlattyType, list):
	"""
	This class is used for typed lists. During flattening and unflattening
	the types are checked and restored.
	
		>>> import flatty
		>>> 
		>>> 
		>>> class Bar(flatty.Schema):
		...	 a_num = int
		...	 a_str = str
		...	 a_thing = None  
		... 
		>>> class Foo(flatty.Schema):
		...	 my_typed_list = flatty.TypedList.set_type(Bar)
		>>> 
		>>> 
		>>> my_bar = Bar(a_num=42, a_str='hello world', a_thing='whatever type here')
		>>> foo = Foo(my_typed_list=[my_bar,])
		>>> 
		>>> flatted = foo.flatit()
		>>> print flatted
		{'my_typed_list': [{'a_num': 42, 'a_str': 'hello world', 'a_thing': 'whatever type here'}]}
		>>> 
		>>> restored_obj = Foo.unflatit(flatted)
		>>> 
		>>> isinstance(restored_obj, Foo)
		True
		>>> isinstance(restored_obj.my_typed_list[0], Bar)
		True
	"""
	pass

class TypedDict(BaseFlattyType, dict):
	"""
	This class is used for typed dict. During flattening and unflattening
	the types are checked and restored.
	
	
		>>> import flatty
		>>> 
		>>> 
		>>> class Bar(flatty.Schema):
		...	 a_num = int
		...	 a_str = str
		...	 a_thing = None  
		... 
		>>> class Foo(flatty.Schema):
		...	 my_typed_dict = flatty.TypedDict.set_type(Bar)
		>>> 
		>>> 
		>>> my_bar = Bar(a_num=42, a_str='hello world', a_thing='whatever type here')
		>>> foo = Foo(my_typed_dict={'my_key':my_bar})
		>>> 
		>>> flatted = foo.flatit()
		>>> print flatted
		{'my_typed_dict': {'my_key': {'a_num': 42, 'a_str': 'hello world', 'a_thing': 'whatever type here'}}}
		>>> 
		>>> restored_obj = Foo.unflatit(flatted)
		>>> 
		>>> isinstance(restored_obj, Foo)
		True
		>>> isinstance(restored_obj.my_typed_dict['my_key'], Bar)
		True
	"""
	pass

class Schema(object):
	"""
	This class builds the base class for all schema classes.
	All schema classes must inherit from this class
	
		>>> import flatty
		>>> 
		>>> class Bar(flatty.Schema):
		...	 a_num = int
		...	 a_str = str
		...	 a_thing = None  
	
	"""
	def __init__(self, **kwargs):
		#to comfortably set attributes via kwargs in the __init__
		for name, value in kwargs.items():
			if not hasattr(self, name):
				raise AttributeError('Attribute not exists')
			setattr(self, name, value)
	
	def flatit(self, cm):
		"""
		one way to flatten the instance of this class
			
		Returns:
			a dict where the instance is flattened to primitive types
		"""
		
		return flatit(self, cm = cm)
	
	@classmethod
	def unflatit(cls, flat_dict, cm):
		"""
		one way to unflatten and load the data back in the schema objects
			
		Returns:
			the object
		"""
		
		return unflatit(cls, flat_dict, cm = cm)		
	

def _check_type(val, type):
	if type == None or val == None or type == types.NoneType:
		return
	if inspect.isclass(type) == False:
		type = type.__class__
	if not isinstance(val, type): 
		raise TypeError(str(val.__class__) + " != " + str(type))
	

class Converter(object):
	"""
	Base class for all Converters. New converters of custom types can be build
	by inherit from this class and implement the following two methods
	
	"""
	
	@classmethod
	def check_type(cls, attr_type, attr_value, cm):
		"""
		should be implemented to check if the attr_type from the schema
		matches the real type of attr_value 
	
		Args:
			attr_type: type from schema
			attr_value: value/obj with unknown type
			
		Returns:
			Nothing if type of attr_value is ok, otherwise should raise
			a TypeError Exception
		"""
		pass
	
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		"""
		need to be implemented to convert a python object to a primitive 
	
		Args:
			obj: the src obj which needs to be converted here
			
		Returns:
			a converted primitive object
		"""
		raise NotImplementedError()
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		"""
		need to be implemented to convert a primitive to a python object 
	
		Args:
			val: the flattened data which needs to be converted here
			
		Returns:
			a converted high level schema object
		"""
		raise NotImplementedError()
	

class DateConverter(Converter):
	"""
	Converter for datetime.date
	
	"""
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		if obj == None:
			return None
			
		return obj.isoformat()
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		if val == None:
			return None
		if obj == None:
			obj = datetime.datetime.strptime(str(val), "%Y-%m-%d").date()
		else:
			d = datetime.datetime.strptime(str(val), "%Y-%m-%d").date()
			obj.replace(d.year, d.month, d.day)
		return obj
	

class DateTimeConverter(Converter):
	"""
	Converter for datetime.datetime
	
	"""
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		if obj == None:
			return None
		return obj.isoformat()
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		if val == None:
			return None
		if obj == None:
			obj = datetime.datetime.strptime(str(val), "%Y-%m-%dT%H:%M:%S.%f")
		else:
			dt = datetime.datetime.strptime(str(val), "%Y-%m-%dT%H:%M:%S.%f")
			obj.replace(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
		return obj

class TimeConverter(Converter):
	"""
	Converter for datetime.time
	
	"""
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		if obj == None:
			return None
		return obj.strftime("%H:%M:%S.%f")
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		if val == None:
			return None
		if obj == None:
			obj = datetime.datetime.strptime(str(val), "%H:%M:%S.%f").time()
		else:
			t = datetime.datetime.strptime(str(val), "%H:%M:%S.%f").time()
			obj.replace(t.hour, t.minute, t.second, t.microsecond, t.tzinfo)
		return obj
	
class SchemaConverter(Converter):
	"""
	Convert basic schema classes
	
	"""
	
	@classmethod
	def check_type(cls, attr_type, attr_value, cm):
		attr_type = attr_type if inspect.isclass(attr_type) else type(attr_type)
		if not issubclass(type(attr_value), attr_type):
			raise TypeError(repr(type(attr_value)) + '!=' + repr(attr_type))
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		if obj == None:
			return None
		if val == None:
			flat_dict = {}
		else:
			flat_dict = val
		
		for attr_name in dir(obj_type):
			if hasattr(obj, attr_name):
				attr_value = getattr(obj, attr_name)
				attr_type = getattr(obj_type, attr_name)
				if not attr_name.startswith('__') and not inspect.ismethod(attr_value):
					
					#set None if types are still present in the object
					# and these are types and not objects
					if attr_value == attr_type and inspect.isclass(attr_value):
						attr_value = None
						
					check_type(attr_type, attr_value, cm)
					
					sub_val = None
					if attr_name in flat_dict:
						sub_val = flat_dict[attr_name]
					
					attr_value = flatit(attr_value, attr_type, sub_val, cm)
					
					flat_dict[attr_name] = attr_value
		return flat_dict
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		if val == None:
			return None
		if obj == None:
			cls_obj = obj_type() if inspect.isclass(obj_type) else type(obj_type)()
		else:
			cls_obj = obj

		#iterate all attributes
		for attr_name in dir(obj_type):
			attr_type = getattr(obj_type, attr_name)
			if not attr_name.startswith('__') and not inspect.ismethod(attr_type):
				#set attr the value of the flat_dict if exists
				flat_val = None
				if attr_name in val:
					flat_val = val[attr_name]
					
					sub_obj = None
					if hasattr(cls_obj, attr_name):
						sub_obj = getattr(cls_obj, attr_name)
					
					conv_attr_value = unflatit(flat_val, attr_type, sub_obj, cm)
					check_type(attr_type, conv_attr_value, cm)
				
					setattr(cls_obj, attr_name, conv_attr_value)
		return cls_obj

class TypedListConverter(Converter):
	"""
	Convert TypedList classes
	
	"""
	
	@classmethod
	def check_type(cls, attr_type, attr_value, cm):
		attr_type = attr_type if inspect.isclass(attr_type) else type(attr_type)
		if not(issubclass(type(attr_value), attr_type) \
			 or issubclass(type(attr_value), list) \
			 or type(attr_value) == types.NoneType):
			raise TypeError(repr(type(attr_value)) + '!=' + repr(attr_type))
	
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		if obj == None:
			return None
		if val == None:
			flat_list = []
		else:
			flat_list = val

		def get_sub_type(idx):
			sub_type = None
			if hasattr(obj_type, 'ftype'):
				sub_type = obj_type.ftype
			elif isinstance(obj_type, list) and len(obj_type) > idx:
				sub_type = obj_type[idx]
			return sub_type
			

		check_type(obj_type, obj, cm)

		for item in obj:
			check_type(get_sub_type(0), item, cm)
			flat_list.append(flatit(item, get_sub_type(0), None, cm))
		return flat_list
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		if val == None:
			return None
		if obj == None:
			cls_obj = obj_type() if inspect.isclass(obj_type) else type(obj_type)()
		else:
			cls_obj = obj
		
		def get_sub_type(idx, v):
			if hasattr(obj_type, 'ftype'):
				sub_type = obj_type.ftype
			elif isinstance(obj_type, list) and len(obj_type) > idx:
				sub_type = obj_type[idx]
			else:
				raise Exception('Can\'t guess type associated with: "'  + v + '"')
			return sub_type
			
		for item in val:
			ret_item = unflatit(item, get_sub_type(0, item), None, cm)
			check_type(get_sub_type(0, item), ret_item, cm)
			cls_obj.append(ret_item)
		return cls_obj
	
	
class TypedDictConverter(Converter):
	"""
	Convert TypedList classes
	
	"""
	
	@classmethod
	def check_type(cls, attr_type, attr_value, cm):
		attr_type = attr_type if inspect.isclass(attr_type) else type(attr_type)
		if not(issubclass(type(attr_value), attr_type) \
			 or issubclass(type(attr_value), dict) \
			 or type(attr_value) == types.NoneType):
			raise TypeError(repr(type(attr_value)) + '!=' + repr(attr_type))
	
	
	@classmethod
	def to_flat(cls, obj_type, obj, val, cm):
		if obj == None:
			return None
		if val == None:
			flat_dict = {}
		else:
			flat_dict = val
		
		def get_sub_type(elem):
			sub_type = None
			if hasattr(obj_type, 'ftype'):
				sub_type = obj_type.ftype
			elif isinstance(obj_type, dict) and elem in obj_type:
				sub_type = obj_type[elem]
			return sub_type

		check_type(obj_type, obj, cm)
		for k, v in obj.items():
			check_type(get_sub_type(k), v, cm)
			
			sub_val = None
			if k in flat_dict:
				sub_val = flat_dict[k]
			
			flat_dict[k] = flatit(v, get_sub_type(k), sub_val, cm)
		return flat_dict
	
	@classmethod
	def to_obj(cls, obj_type, val, obj, cm):
		if val == None:
			return None
		if obj == None:
			cls_obj = obj_type() if inspect.isclass(obj_type) else type(obj_type)()
		else:
			cls_obj = obj
		
		def get_sub_type(elem, v):
			if hasattr(obj_type, 'ftype'):
				sub_type = obj_type.ftype
			elif isinstance(obj_type, dict) and elem in obj_type:
				sub_type = obj_type[elem]
			else:
				raise Exception('Can\'t guess type associated with: "'  + v + '"')
			return sub_type
		
		for k, v in val.items():
			sub_obj = None
			if hasattr(cls_obj, k):
				sub_obj = getattr(cls_obj, k)

			ret_v = unflatit(v, get_sub_type(k, v), sub_obj, cm)

			check_type(get_sub_type(k, v), ret_v, cm)
			cls_obj[k] = ret_v
		return cls_obj
	

class ConvertManager(object):
	"""
	Class for managing the converters
	
	"""
	
	_convert_dict = {
				datetime.date:{'conv':DateConverter, 'exact':True},
				datetime.datetime:{'conv':DateTimeConverter, 'exact':True},
				datetime.time:{'conv':TimeConverter, 'exact':True},
				Schema:{'conv':SchemaConverter, 'exact':False},
				TypedDict:{'conv':TypedDictConverter, 'exact':True},
				dict:{'conv':TypedDictConverter, 'exact':True},
				TypedList:{'conv':TypedListConverter, 'exact':True},
				list:{'conv':TypedListConverter, 'exact':True},
			}
	
	@classmethod
	def to_flat(cls, obj_type, obj, val):
		"""
		calls the right converter and converts to a flat type
	
		Args:
			val_type: the type of the object
			
			obj: the object which should be converted
			
		Returns:
			a converted primitive object"""

		obj_type_class = obj_type if inspect.isclass(obj_type) else obj_type.__class__
		for type in cls._convert_dict:
			#String comparisson is okay here since we compare schema against
			#object types which can differ in the ftype class variable therefore
			#string compare is correct and direct type compare fails
			if str(obj_type_class) == str(type):
				return cls._convert_dict[type]['conv'].to_flat(obj_type, obj, val, cls)
		
		for type in cls._convert_dict:
			if cls._convert_dict[type]['exact'] == False and issubclass(obj_type_class, type):
				return cls._convert_dict[type]['conv'].to_flat(obj_type, obj, val, cls)
			
		return obj
	
	@classmethod
	def to_obj(cls, obj_type, val, obj):
		"""
		calls the right converter and converts the flat val to a schema
		object
	
		Args:
			val_type: the type to which we want to convert
			
			val: the flattened data which needs to be converted here
			
		Returns:
			a converted high level schema object
		"""
		
		obj_type_class = obj_type if inspect.isclass(obj_type) else obj_type.__class__
		for type in cls._convert_dict:
			#String comparisson is okay here since we compare schema against
			#object types which can differ in the ftype class variable therefore
			#string compare is correct and direct type compare fails
			if str(obj_type_class) == str(type):
				return cls._convert_dict[type]['conv'].to_obj(obj_type, val, obj, cls)
		
		for type in cls._convert_dict:
			if cls._convert_dict[type]['exact'] == False and issubclass(obj_type_class, type):
				return cls._convert_dict[type]['conv'].to_obj(obj_type, val, obj, cls)
			
		return val
	
	@classmethod
	def check_type(cls, attr_type, attr_value):
		"""
		checks the type of value and type
		
		Args:
			attr_type: the type which the attr_value should have
			
			attr_value: obj which we check against attr_type
			
		Returns:
			None if everything is ok, otherwise raise TypeError
		"""
		if attr_type:
			attr_type_class = attr_type if inspect.isclass(attr_type) else attr_type.__class__
			for type in cls._convert_dict:
				#String comparisson is okay here since we compare schema against
				#object types which can differ in the ftype class variable therefore
				#string compare is correct and direct type compare fails
				if str(attr_type_class) == str(type):
					cls._convert_dict[type]['conv'].check_type(attr_type, attr_value, cls)
					return
				
			for type in cls._convert_dict:
				if cls._convert_dict[type]['exact'] == False and issubclass(attr_type_class, type):
					cls._convert_dict[type]['conv'].check_type(attr_type, attr_value, cls)
					return
		else:
			attr_type_class = attr_type
		_check_type(attr_value, attr_type_class)
	
	@classmethod
	def set_converter(cls, conv_type, converter, exact=True):
		"""
		sets a converter object for a given `conv_type`
	
		Args:
			conv_type: the type for which the converter is responsible
				
			converter: a subclass of the :class:`Converter` class
			
			exact: When True only matches converter if type of obj is
				the type of the converter. If exact=False then converter
				matches also if obj is just a subclass of the converter type.
				E.g the Schema Class is added to the converter with exact=False
				because Schema Classes are always inherited at least once.
				(default=True) 
		"""
		if inspect.isclass(converter) and \
			issubclass(converter, Converter):
			cls._convert_dict[conv_type] = {}
			cls._convert_dict[conv_type]['conv'] = converter
			cls._convert_dict[conv_type]['exact'] = exact
		else:
			raise TypeError('Subclass of Converter expected')
	
	@classmethod
	def del_converter(cls, conv_type):
		"""deletes the converter object for a given `conv_type`"""
		if conv_type in cls._convert_dict:
			del cls._convert_dict[conv_type]
		
	

def check_type(attr_type, attr_value, cm = ConvertManager):
	"""
	check the type of attr_value against attr_type
	
		Args:
			attr_type: a type
			attr_value: an object
	
		Returns:
			None in normal cases, if attr_type doesn't match type of
			attr_value, raise TypeError
	"""
	
	cm.check_type(attr_type, attr_value)


def flatit(obj, obj_type=None, val=None, cm = ConvertManager):
	"""
	one way to flatten the `obj`
	
		Args:
			obj: a :class:`Schema` instance which will be flatted
	
		Returns:
			a dict where the obj is flattened to primitive types
	"""
	
	if obj_type == None:
		obj_type = type(obj)
	return cm.to_flat(obj_type, obj, val)


def unflatit(val, obj_type, obj=None, cm = ConvertManager):
	"""
	one way to unflatten and load the data back in the `cls`
	
		Args:
			flat_dict: a flat dict which will be loaded into an instance of
				the `cls_or_obj`
			cls_or_obj: the class from which the instance is builded, or an
				an existing instance where the data is merged
			
		Returns:
			an instance of type `cls`
	"""
	
	return cm.to_obj(obj_type, val, obj)

