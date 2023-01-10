""" Write and read back list issue 10 """

import attr
from fgpyo.util.metric import Metric
from pathlib import Path
from typing import List
from typing import Any
from typing import Type
from typing import Optional

@attr.s(auto_attribs=True, frozen=True)
class Person(Metric["Person"]):
    name: List[str]
    age: List[int]

#t = Person(name=None, age=30)
#print(type(getattr(Person, name)))
#print(type(Person.name))
#metrics = [
#    Person(name="alice", age=30),
#    Person(name="", age="")
#]

#assert Person(name="", age=42).formatted_values() == ([None, "42"])
#p = Person(name = ["", "Sally"], age=43)
#y = "{" + ",".join(str(p.format_value(v)) for v in p.name) + "}"
#print(y)
#assert Person(name=["", "Sally"], age=43) == ([[None, "Sally"], 43])
#print(Person(name=["", "Sally"], age=43).formatted_values())

#p = Person(name = None, age=None)
#print()
assert Person.parse(fields=["Sally, John", "40, 30"]) == Person(name=['Sally', ' John'], age=[40, 30])
#print(p.formatted_values())
##Person.write(Path("metrics.txt"), *metrics)
#r = Person.read(path=Path("metrics.txt"))
#
# print message = 
#[Person(name=['Alice', 'Sandy', 'Max'], age=[40, 56, 39]), Person(name=['Bob'], age=[24])]
#print(Person.header())
#print(Person(name=None, age=42).formatted_values())
