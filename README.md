# Stiffened_plate_solid solid单元

1. 此脚本为abaqus参数化建模，自动生成横纵交错的平板加强筋构件，参数化修改横纵加强筋的数量并进行屈曲分析

2. 可参数化选择金属材料属性或复合材料材料属性，并输入相应的材料参数

3. 平板和加强筋分别采用shell单元、beam单元进行建模，如是复合材料的平板，平板部分可选铺层层数，加强筋的材料属性用ABD等效刚度

4. 横纵加强筋的数量为交互输入参数

实现平板加强筋构件有限元模型的自动生成，进行加强筋平板屈曲分析的快速分析
