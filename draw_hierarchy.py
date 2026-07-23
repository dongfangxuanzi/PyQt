import matplotlib.pyplot as plt
import networkx as nx

# 创建一个有向图
G = nx.DiGraph()

# 添加节点和边
G.add_node("Root")
G.add_edge("Root", "Child1")
G.add_edge("Root", "Child2")
G.add_edge("Child1", "Grandchild1")
G.add_edge("Child1", "Grandchild2")
G.add_edge("Child2", "Grandchild3")

# 绘制图形
pos = nx.nx_agraph.graphviz_layout(G, prog='dot')  # 使用Graphviz的布局算法
nx.draw(G, pos, with_labels=True, arrows=True, node_color='lightblue', node_size=3000, arrowstyle='-|>', arrowsize=20)
plt.savefig('plot.png')
plt.show()
