'''
Name:        render.py
Purpose:     使用matplotlib渲染生成类层次图
Author:      wukan
Created:     2026-07-25
Copyright:   (c) wukan 2026
Licence:     Mulan
'''
import argparse
import os
import logging
import matplotlib.pyplot as plt
import networkx as nx
import json


PLOT_IMAGE_NAME = 'plot.png'


def main(class_file, outpath):
    # 创建一个有向图
    g = nx.DiGraph()
    
    with open(class_file) as file:
        class_base_data = json.load(file)

    # 添加节点和边
    g.add_node("Root")
    g.add_edge("Root", "Child1")
    g.add_edge("Root", "Child2")
    g.add_edge("Child1", "Grandchild1")
    g.add_edge("Child1", "Grandchild2")
    g.add_edge("Child2", "Grandchild3")

    # 绘制图形
    pos = nx.nx_agraph.graphviz_layout(g, prog='dot')  # 使用Graphviz的布局算法
    nx.draw(
        g,
        pos,
        with_labels=True,
        arrows=True,
        node_color='lightblue',
        node_size=3000,
        arrowstyle='-|>',
        arrowsize=20
    )
    plt.savefig(os.path.join(outpath, PLOT_IMAGE_NAME))
    #plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--class-file",
        type=str,
        dest="class_file",
        help='class hierarchy file',
        required=True
    )
    parser.add_argument(
        "-o",
        "--outpath",
        type=str,
        dest="out_path",
        help='fig save to path',
        required=True
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    main(args.class_file, args.out_path)
