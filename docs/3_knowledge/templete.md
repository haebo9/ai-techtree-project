---
title: "개념 명 (예: Python Class & OOP)"
topic: "Python"
category: "Basic" # Basic, Intermediate, Advanced, Deep-Dive
tags: ["OOP", "Class", "Inheritance", "Magic Methods"]
last_updated: "2025-12-04"
---

# 📘 개념 정의 (Definition)
> **한 줄 요약:** 이 개념이 무엇인지, 면접에서 대답할 수 있는 수준으로 한 문장으로 정의합니다.

* **핵심 키워드:** #키워드1 #키워드2
* **유사 개념:** (비교할만한 다른 개념, 예: Java의 Class와 비교)

---

## 1. 기본 문법 (Syntax & Basic Usage)
가장 기초적인 사용법을 작성합니다.

```python
# 기본 문법 예시
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        return "Woof!"

my_dog = Dog("Buddy")
print(my_dog.bark())