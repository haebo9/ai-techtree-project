from streamlit_agraph import Node
n = Node(id="test", label="test", size=20, color={"background": "#E0E0E0", "border": "#FF0000"})
print(n.__dict__)
