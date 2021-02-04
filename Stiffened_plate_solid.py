#!/user/bin/python
#-*-coding:UTF-8-*-

#文件名：Stiffened_plate_solid.py

#运行该脚本将自动实现加筋平板的屈曲分析
import math

from abaqus import *
import testUtils
testUtils.setBackwardCompatibility()
from abaqusConstants import *

#建立模型
myModel = mdb.Model(name='Stiffened_plate_solid')
#删除自动创建的Model-1
#del mdb.models['Model-1']

#创建新视口
#myViewport = session.Viewport(name='Stiffened_plate_solid',
#    origin=(0,0),width=150,height=120)

#导入part模块
import part
import regionToolset

tol = 0.1

#输入Plate几何参数        thicknessperply用于划分网格时分层
t_fields = (('Length (mm)','500'),('Width (mm)','200'),('Thickness (mm)','4'),('Thickness per ply (mm)','2'))
p_Length, p_Width, p_Thickness, p_Thicknessperply = getInputs(fields=t_fields, label='Plate dimensions:', dialogTitle='Create Plate')
length = float(p_Length)
width = float(p_Width)
thickness = float(p_Thickness)
thicknessperply = float(p_Thicknessperply)

#创建草图
myPlateSketch = myModel.ConstrainedSketch(name='Stiffened_plate_solid',sheetSize=1000.0)

#绘制平板
myPlateSketch.rectangle(point1=(0.0,0.0), point2=(length,width))

#创建平板模型
myPlatePart = myModel.Part(name='Stiffened_plate_solid', 
    dimensionality=THREE_D, type=DEFORMABLE_BODY)

#拉伸创建三维平板
myPlatePart.BaseSolidExtrude(sketch=myPlateSketch, depth=thickness)
#myViewport.setValues(displayedObject=myPlatePart)

#创建XY基准平面           
datumPlaneXY = myPlatePart.DatumPlaneByPrincipalPlane(principalPlane=XYPLANE, offset=0.0)
name_datumXY = 'Datum plane-XY'
myPlatePart.features.changeKey(fromName=datumPlaneXY.name, toName=name_datumXY)   #???结合？

#创建YZ基准平面
datumPlaneYZ = myPlatePart.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=0.0)
name_datumYZ = 'Datum plane-YZ'
myPlatePart.features.changeKey(fromName=datumPlaneYZ.name, toName=name_datumYZ)

#创建XZ基准平面
datumPlaneXZ = myPlatePart.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=0.0)
name_datumXZ = 'Datum plane-XZ'
myPlatePart.features.changeKey(fromName=datumPlaneXZ.name, toName=name_datumXZ)

#创建基准Z轴
datumAxisZ = myPlatePart.DatumAxisByPrincipalAxis(principalAxis=ZAXIS)
name_datumZaxis = 'Datum axis-Z'
myPlatePart.features.changeKey(fromName=datumAxisZ.name, toName=name_datumZaxis)


#创建平板的set：set-plate             
Platecells = myPlatePart.cells.findAt(((0,0,0),))
myPlatePart.Set(name='Set-plate', cells=(Platecells,))

#给Plate分层  用总厚度thickness和thickperply厚度取余
num_PlateLayer = 0
if(thickness%thicknessperply==0):
    num_PlateLayer = int(thickness/thicknessperply)
else:
    num_PlateLayer = int(thickness/thicknessperply)+1       #写完判断或循环一定要记得换行！！

#画分割点
datums = [0 for _ in range(num_PlateLayer-1)]
i = 0
while (i<num_PlateLayer-1):
    datums[i] = myPlatePart.DatumPointByOffset(point=(0,0,0), vector=(0,0,(i+1)*thicknessperply))
    i = i+1

#利用边界点切割Plate
i = 0
while (i<num_PlateLayer-1):
    ptncell = myPlatePart.cells.findAt(((0,0,(i+1)*thicknessperply),))
    ptn_edge = myPlatePart.edges.findAt((0,0,(i+1)*thicknessperply-tol),)
    myPlatePart.PartitionCellByPlanePointNormal(point=(0,0,(i+1)*thicknessperply), normal=ptn_edge, cells=ptncell)    #point=datums[i]是错的？
    i = i+1

#对分割后的Plate逐层创建set：Set-Plate i   从下往上是set-Plate 1-n
i = 0
while (i<num_PlateLayer):
    cord1 = (0,0,(i)*thicknessperply+tol)
    Platecell = myPlatePart.cells.findAt((cord1,),)
    setname = 'Set-LayerPla'+str(i+1)                                                   
    myPlatePart.Set(name=setname, cells=(Platecell,))
    i = i+1

#输入与载荷平行方向的加强筋St的参数  注意要float参数
t_fields = (('S_Height (mm)','10'),('S_UpWidth (mm)','8'),('S_BotWidth (mm)','8'),('S_Pitch (mm)','25'),('S_Number (mm)','8'),)
p_SHeight, p_SUpWidth, p_SBotWidth, p_SPitch, p_SNum = getInputs(fields=t_fields, label='Stringer Dimension:', dialogTitle='Create Stringer')
Sheight = float(p_SHeight)
Supwidth = float(p_SUpWidth)
Sbotwidth = float(p_SBotWidth)
if (Supwidth>Sbotwidth):         #保证梯形形式
         Supwidth = Sbotwidth           #没有end，但要空行

Snum = int(p_SNum)
Spitch = float(p_SPitch)

#判断加筋是否符合规则  待改正
#if (width<(Snum-1)*Spitch+Sbotwidth):
#   reply = getWarningReply(message='重新填写加筋尺寸', buttons=(YES,NO))
#        if reply = = YES:
#            print'click YES'
#        elif reply = = NO:
#            print'click NO'

#计算plate端面到第一个stringer的距离  eachsideLeft为Stringer到端面距离，和Left没关系
eachsideleft = (width-(Snum-1)*Spitch-Sbotwidth)/2        
#相邻stringer之间的距离
disStringer = Spitch-Sbotwidth
#加强筋Stringer上下底差的一半  
dw = (Sbotwidth-Supwidth)/2

#绘制加强筋Stringer的草图
upedge = myPlatePart.edges.findAt((0,width/2,thickness),)
upface = myPlatePart.faces.findAt((0,width/2,thickness-tol),)
tr = myPlatePart.MakeSketchTransform(sketchPlane=upface, sketchUpEdge=upedge, 
    sketchPlaneSide=SIDE1, sketchOrientation=RIGHT, origin=(0.0, 0.0, 0.0))
sk = myModel.ConstrainedSketch(name='StringerProfile', 
    sheetSize=10000, gridSpacing=250, transform=tr)
#myPlatePart.projectReferencesOntoSketch(sketch=sk, filter=COPLANAR_EDGES)   ???
#绘制首个加强筋Stringer截面
p1 = (thickness,eachsideleft)
p2 = (Sheight+thickness,eachsideleft+dw)
p3 = (Sheight+thickness,eachsideleft+Supwidth+dw)
p4 = (thickness,eachsideleft+Sbotwidth)
sk.Line(p1, p2)
sk.Line(p2, p3)
sk.Line(p3, p4)
sk.Line(p4, p1)
#阵列  geomList=sk.geometry.values()表示拾取草图上的所有内容
sk.linearPattern(geomList=sk.geometry.values(), vertexList=(), number1=1, 
    spacing1=40.007, angle1=0.0, number2=Snum, spacing2=Spitch, angle2=-270)


#沿平行压力方向拉伸形成Stringer
myPlatePart.SolidExtrude(sketchPlane=upface, sketchUpEdge=upedge, sketchPlaneSide=SIDE1, 
    sketchOrientation=RIGHT, sketch=sk, depth=length, flipExtrudeDirection=ON, 
    keepInternalBoundaries=ON)

#为加强筋Stringer创建set   框选命令getByBoundingBox(...),和cae操作不一样，最后的拾取为完全选中的部分，选一半的不算拾取
#strcords = [0 for _ in range(Snum)]    
#i = 0
tol = 0.1
Stringercells = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-width,yMax=width,zMin=thickness-tol,zMax=thickness+Sheight+tol)
myPlatePart.Set(name='Set-Stringers',cells=(Stringercells,))

#888888888888888888888888888
#给Stringer分层  用总厚度Sheight和thickperply厚度取余
num_StringerLayer = 0
if(Sheight%thicknessperply==0):
    num_StringerLayer = int(Sheight/thicknessperply)
else:
    num_StringerLayer = int(Sheight/thicknessperply)+1       #写完判断或循环一定要记得换行！！

#画分割点
datums = [0 for _ in range(num_StringerLayer-1)]
i = 0
while (i<num_StringerLayer-1):
    datums[i] = myPlatePart.DatumPointByOffset(point=(0,0,0), vector=(0,0,(i+1)*thicknessperply+thickness))
    i = i+1

#利用边界点切割Stringer
i = 0
while (i<num_StringerLayer-1):
    ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-width,yMax=width,
        zMin=thickness-tol+i*thicknessperply,zMax=thickness+Sheight+tol)
    ptn_edge = myPlatePart.edges.findAt((0,0,tol),)
    myPlatePart.PartitionCellByPlanePointNormal(point=(0,0,(i+1)*thicknessperply+thickness), normal=ptn_edge, cells=ptncell)    #point=datums[i]是错的？
    i = i+1

#对分割后的Stringer逐层创建set：Set-LayerStr i   从下往上是set-layerStri 1到n
i = 0
while (i<num_StringerLayer):
    Stringercell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-width,yMax=width,
        zMin=thickness-tol+i*thicknessperply,zMax=thickness+(i+1)*thicknessperply+tol)
    setname = 'Set-LayerStr'+str(i+1)                                                   
    myPlatePart.Set(name=setname, cells=(Stringercell,))
    i = i+1

#沿垂直压力方向创建Frame
#输入与载荷垂直方向的加强筋Frame的参数，注意要float参数
t_fields = (('F_Height (mm)','10'),('F_UpWidth (mm)','8'),('F_BotWidth (mm)','8'),('F_Pitch (mm)','50'),('F_Number (mm)','10'),)
p_FHeight, p_FUpWidth, p_FBotWidth, p_FPitch, p_FNum = getInputs(fields=t_fields, label='Frame Dimension:', dialogTitle='Create Frame')
Fheight = float(p_FHeight)
Fupwidth = float(p_FUpWidth)
Fbotwidth = float(p_FBotWidth)
if (Fupwidth>Fbotwidth):         #保证梯形形式
         Fupwidth = Fbotwidth           #没有end，但要空行

Fnum = int(p_FNum)
Fpitch = float(p_FPitch)

#计算plate端面到第一个Frame的距离  eachsideRight为Frame到端面距离，和Right没关系
eachsideRight = (length-(Fnum-1)*Fpitch-Fbotwidth)/2        
#相邻Frame之间的距离
disFrame = Fpitch-Fbotwidth
#加强筋Frame上下底差的一半  
dw = (Fbotwidth-Fupwidth)/2
#绘制加强筋Frame的草图
upedge = myPlatePart.edges.findAt((length/2,0,thickness),)
upface = myPlatePart.faces.findAt((length/2,0,thickness-tol),)
tr = myPlatePart.MakeSketchTransform(sketchPlane=upface, sketchUpEdge=upedge, 
    sketchPlaneSide=SIDE1, sketchOrientation=RIGHT, origin=(0.0, 0.0, 0.0))
sk = myModel.ConstrainedSketch(name='FrameProfile', 
    sheetSize=10000, gridSpacing=250, transform=tr)
#绘制首个加强筋Frame截面
p1 = (thickness,-eachsideRight)
p2 = (Fheight+thickness,-(eachsideRight+dw))
p3 = (Fheight+thickness,-(eachsideRight+Fupwidth+dw))
p4 = (thickness,-(eachsideRight+Fbotwidth))
sk.Line(p1, p2)
sk.Line(p2, p3)
sk.Line(p3, p4)
sk.Line(p4, p1)
#阵列  geomList=sk.geometry.values()表示拾取草图上的所有内容
sk.linearPattern(geomList=sk.geometry.values(), vertexList=(), number1=1, 
    spacing1=40.007, angle1=0.0, number2=Fnum, spacing2=Fpitch, angle2=-90)


#沿平行压力方向拉伸形成Frame
myPlatePart.SolidExtrude(sketchPlane=upface, sketchUpEdge=upedge, sketchPlaneSide=SIDE1, 
    sketchOrientation=RIGHT, sketch=sk, depth=width, flipExtrudeDirection=ON, 
    keepInternalBoundaries=ON)

#为Frame创建set   88888888888888888888不能这样在array里存cell作为一个cells？
#i = 0
#Framecells = [0 for _ in range(Fnum+1)]
#while (i<Fnum+1):
#    if(i==0):
#        Framecells[i] = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=0-tol,yMax=eachsideleft+tol,
#        zMin=thickness-tol,zMax=thickness+Fheight+tol)
#    else:
#        Framecells[i] = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=eachsideleft+(i-1)*Spitch+tol,yMax=eachsideleft+i*Spitch+tol,
#        zMin=thickness-tol,zMax=thickness+Fheight+tol)
#    i = i+1
#  88888888888888888888888888888888

#为Frame创建set:Set-Frame
strcords = [0 for _ in range(Snum+1)*Fnum]
i = 0
while (i<Snum+1):
    j = 0
    while (j<Fnum):
        if(i==0):
            tempx = eachsideRight+j*Fpitch+Fbotwidth/2
            tempy = eachsideleft/2
            tempz = thickness+Fheight
        elif(i==Snum):
            tempx = eachsideRight+j*Fpitch+Fbotwidth/2
            tempy = width-tol
            tempz = thickness+Fheight
        else:
            tempx = eachsideRight+j*Fpitch+Fbotwidth/2
            tempy = eachsideleft+i*Spitch-tol
            tempz = thickness+Fheight
        strcords[i*Fnum+j] = (tempx, tempy, tempz)
        j = j+1
    i = i+1

Framecells = myPlatePart.cells.findAt(coordinates=strcords)
myPlatePart.Set(name='Set-Frames',cells=(Framecells,))

#分层切割Frame
#利用边界点切割Frame      (利用Stringer中画的点切割Frame，此脚本Stringer和Frame设置成等高)
i = 0
while (i<num_StringerLayer-1):
    Framecells = myPlatePart.cells.findAt(coordinates=strcords)
    ptn_edge = myPlatePart.edges.findAt((0,0,tol),)
    myPlatePart.PartitionCellByPlanePointNormal(point=(0,0,(i+1)*thicknessperply+thickness), normal=ptn_edge, cells=Framecells)    #point=datums[i]是错的？
    i = i+1


#对分割后的Frame逐层创建set：Set-LayerFra i   从下往上是set-layerFrai 1到n  
#因为等高(num_StringeLayer=n)，所以未设置num_FrameLayer，此处切割和之后的铺层都用num_StringerLayer     
k = 0
while (k<num_StringerLayer):
    strcords = [0 for _ in range(Snum+1)*Fnum]
    i = 0
    while (i<Snum+1):
        j = 0
        while (j<Fnum):
            if(i==0): 
                tempx = eachsideRight+j*Fpitch+Fbotwidth/2
                tempy = eachsideleft/2
                tempz = thickness+k*thicknessperply+tol
            elif(i==Snum):
                tempx = eachsideRight+j*Fpitch+Fbotwidth/2
                tempy = width-tol
                tempz = thickness+k*thicknessperply+tol
            else:
                tempx = eachsideRight+j*Fpitch+Fbotwidth/2
                tempy = eachsideleft+i*Spitch-tol
                tempz = thickness+k*thicknessperply+tol
            strcords[i*Fnum+j] = (tempx, tempy, tempz)
            j = j+1
        i = i+1
    Framecells = myPlatePart.cells.findAt(coordinates=strcords)
    setname = 'Set-LayerFra'+str(k+1)                                                   
    myPlatePart.Set(name=setname, cells=(Framecells,))
    k = k+1


#厚度方向切割Plate，保证网格不畸形
#沿Stringer一个端点切
i = 0
while (i<Snum):
    if(i==0):
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-tol,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((0,tol,0),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(0,eachsideleft,thickness), normal=ptn_edge, cells=ptncell)    #point=datums[i]是错的？
    else:
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=eachsideleft+(i-1)*Spitch-tol,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((0,tol,thickness),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(0,eachsideleft+i*Spitch,thickness), normal=ptn_edge, cells=ptncell)     
    i = i+1

#沿Stringer另一个端点切
i = 0
while (i<Snum):
    if(i==0):
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-tol,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((0,tol,0),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(0,eachsideleft+Sbotwidth,thickness), normal=ptn_edge, cells=ptncell)   
    else:
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=eachsideleft+(i-1)*Spitch+Sbotwidth-tol,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((0,tol,thickness),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(0,eachsideleft+i*Spitch+Sbotwidth,thickness), normal=ptn_edge, cells=ptncell)     
    i = i+1

#厚度方向切割Plate，保证网格不畸形
#沿Frame一个端点切
i = 0
while (i<Fnum):
    if(i==0):
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-tol,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((tol,0,0),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(eachsideRight,0,thickness), normal=ptn_edge, cells=ptncell)    #point=datums[i]是错的？
    else:
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=eachsideRight+(i-1)*Fpitch-tol,xMax=length+tol,yMin=-width,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((tol,0,0),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(eachsideRight+i*Fpitch,0,thickness), normal=ptn_edge, cells=ptncell)     
    i = i+1

#沿Frame另一个端点切
i = 0
while (i<Fnum):
    if(i==0):
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length,yMin=-tol,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((tol,0,0),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(eachsideRight+Fbotwidth,0,thickness), normal=ptn_edge, cells=ptncell)   
    else:
        ptncell = myPlatePart.cells.getByBoundingBox(xMin=eachsideRight+(i-1)*Fpitch+Fbotwidth-tol,xMax=length+tol,yMin=-width,yMax=width+tol,
            zMin=-tol,zMax=thickness+tol)
        ptn_edge = myPlatePart.edges.findAt((tol,0,0),)
        myPlatePart.PartitionCellByPlanePointNormal(point=(eachsideRight+i*Fpitch+Fbotwidth,0,thickness), normal=ptn_edge, cells=ptncell)     
    i = i+1


#导入Assembly模块
import assembly 

#创建实例部件
myAssembly = myModel.rootAssembly
myInstance = myAssembly.Instance(name='Stiffened_plate_solid-1', part=myPlatePart, dependent=ON)

#导入step模块
import step 

#在初始分析步Initial之后创建一个分析步Buckle
myModel.BuckleStep(name='Buckle', 
    previous='Initial', numEigen=10, vectors=18)

#导入load模块
import load

#通过坐标找到左右两个端面
LeftEndCenter = (0,100,2)
LeftEnd = myInstance.faces.findAt((LeftEndCenter),)
LeftEnds = LeftEnd.getFacesByFaceAngle(20)
myAssembly.Set(name='LeftEnd',faces=LeftEnds)
RightEndCenter = (500,100,2)
RightEnd = myInstance.faces.findAt((RightEndCenter),)
RightEnds = RightEnd.getFacesByFaceAngle(20)
myAssembly.Set(name='RightEnd',faces=RightEnds)

#在左右两端面创建固定约束
LeftRegion = myAssembly.sets['LeftEnd']
#LeftRegion = regionToolset.Region(side1Faces=LeftEnds)
myModel.DisplacementBC(name='LeftEnd', 
    createStepName='Initial', region=LeftRegion, u1=UNSET, u2=SET, u3=SET, 
    ur1=UNSET, ur2=UNSET, ur3=UNSET, amplitude=UNSET, distributionType=UNIFORM, 
    fieldName='', localCsys=None)
RightRegion = myAssembly.sets['RightEnd']
#RightRegion = regionToolset.Region(side1Faces=RightEnds)
myModel.DisplacementBC(name='RightEnd', 
    createStepName='Initial', region=RightRegion, u1=SET, u2=SET, u3=SET, ur1=UNSET, 
    ur2=UNSET, ur3=UNSET, amplitude=UNSET, distributionType=UNIFORM, 
    fieldName='', localCsys=None)

#在左端面施加压强载荷
#通过坐标找到左端面
LeftSurfaceCenter = (0,100,2)
LeftSurface = myInstance.faces.findAt((LeftSurfaceCenter),)
LeftSurfaces = LeftSurface.getFacesByFaceAngle(20)
myAssembly.Set(name='Axis_surf',faces=LeftSurfaces)
#AxisSurface = myAssembly.sets['Axis_surf']
AxisRegion = regionToolset.Region(side1Faces=LeftSurfaces)          
myModel.Pressure(name='Axis-Pressure', 
    createStepName='Buckle', region=AxisRegion, distributionType=UNIFORM, field='', 
    magnitude=1.0)

#导入mesh模块
import mesh 

#为部件指定单元类型
Regions = (myPlatePart.cells,)
elemType1 = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD, 
    kinematicSplit=AVERAGE_STRAIN, secondOrderAccuracy=OFF, 
    hourglassControl=DEFAULT, distortionControl=DEFAULT)
elemType2 = mesh.ElemType(elemCode=C3D6, elemLibrary=STANDARD)
elemType3 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
myPlatePart.setElementType(regions=Regions, elemTypes=(elemType1, elemType2, elemType3))
#elemType = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD)

#为零件整体撒种子
myPlatePart.seedPart(size=2 ,deviationFactor=0.1, minSizeFactor=0.1)

#为零件生成网格
myPlatePart.generateMesh()

#设置网格堆叠方向
ref_face = myPlatePart.faces.findAt((tol, eachsideleft+tol, thickness+Sheight),)
myPlatePart.assignStackDirection(referenceRegion=ref_face, cells=myPlatePart.cells)


# 显示划分网格后的实例模型        ??
#myViewport.assemblyDisplay.setValues(mesh = ON)
#myViewport.assemblyDisplay.meshOptions.setValues(meshTechnique = ON)
#myViewport.setValues(displayedObject = myAssembly)

#导入material模块
import material

stepindex = getInput('Enter the material type (1.Composite; 2.Metal):')
stepindex = int(stepindex)
if (stepindex==2):
#创建金属材料
    mat_Matel = myModel.Material(name='Metal')
#输入金属材料属性
    t_fields = (('Density(t/mm3)','1.6E-009'),('E(MPa)','200000'),('Nu','0.3'))
    m_Den, m_E, m_Nu = getInputs(fields=t_fields,label='Material parameter:', dialogTitle='Create Metal')
    mat_Density = float(m_Den)
    mat_E = float(m_E)
    mat_Nu = float(m_Nu)
#定义材料属性
    mat_Density = 1.6E-009
    mat_E = 200000
    mat_Nu = 0.3
#创建材料参数
    mat_Matel.Density(table=((mat_Density,),))
    isotropic = (mat_E,mat_Nu)
    mat_Matel.Elastic(type=ISOTROPIC, table=(isotropic,))
    #***********分割线
    #创建section
    import section
    myModel.HomogeneousSolidSection(name='Metal-Homo', 
        material='Metal', thickness=None)
    Metalcells = myPlatePart.cells.getByBoundingBox(xMin=-length,xMax=length+tol,yMin=-width,yMax=width+tol,
        zMin=-thickness,zMax=thickness+Sheight+tol)
    region = regionToolset.Region(cells=Metalcells)
    myPlatePart.SectionAssignment(region=region, sectionName='Metal-Homo', offset=0.0, 
        offsetType=MIDDLE_SURFACE, offsetField='',thicknessAssignment=FROM_SECTION)
elif (stepindex==1):
#创建复合材料
    mat_lam = myModel.Material(name='Laminate')
#输入单层板材料参数(交互)
    t_fields = (('Density(t/mm3)','1.6E-009'),('E1(MPa)','155000'),('E2(MPa)','9420'),('E3(MPa)','9420'),
        ('Nu12','0.27'),('Nu13','0.27'),('Nu23','0.3'),('G12(MPa)','5400'),('G13(MPa)','5400'),('G23(MPa)','3900'))
    m_Den, m_E1, m_E2, m_E3, m_Nu12, m_Nu13, m_Nu23, m_G12, m_G13, m_G23 = getInputs(fields=t_fields,
        label='Material parameter:', dialogTitle='Create Laminate')
    mat_Density = float(m_Den)
    mat_E1 = float(m_E1)
    mat_E2 = float(m_E2)
    mat_E3 = float(m_E3)
    mat_Nu12 = float(m_Nu12)
    mat_Nu13 = float(m_Nu13)
    mat_Nu23 = float(m_Nu23)
    mat_G12 = float(m_G12)
    mat_G13 = float(m_G13)
    mat_G23 = float(m_G23)
#定义材料属性
    mat_Density = 1.6E-009
    mat_E1 = 155000.0
    mat_E2 = 9420.0
    mat_E3 = 9420.0
    mat_Nu12 = 0.27
    mat_Nu13 = 0.27
    mat_Nu23 = 0.3
    mat_G12 = 5400
    mat_G13 = 5400
    mat_G23 = 3900
#创建材料参数
    mat_lam.Density(table=((mat_Density,),))
    engineering_constants = (mat_E1,mat_E2,mat_E3,mat_Nu12,mat_Nu13,
        mat_Nu23,mat_G12,mat_G13,mat_G23)
    mat_lam.Elastic(type=ENGINEERING_CONSTANTS, table=(engineering_constants,))
    #创建section
    import section
    #建立直角坐标系         8888888888888888888
    Layup = myPlatePart.DatumCsysByThreePoints(name='Layup',coordSysType=CARTESIAN,
        origin=(0,0,0),point1=(1,0,0),point2=(0,1,0))
    #创建plate铺层
    layupOrientation = myPlatePart.datums[Layup.id]
    compositeLayup = myPlatePart.CompositeLayup(
        name='plate', description='', elementType=SOLID, symmetric=False, 
        thicknessAssignment=FROM_SECTION)
    #***********分割线
    compositeLayup.ReferenceOrientation(orientationType=SYSTEM, 
        localCsys=layupOrientation, fieldName='', 
        additionalRotationType=ROTATION_NONE, angle=0.0, 
        additionalRotationField='', axis=AXIS_3, stackDirection=STACK_3)
    #***********分割线
    laythickness = 0.25
    #totalLayerNum = ceil(thickness/laythickness) ;thickness=4
    totalLayerNum = ceil(thickness/laythickness)
    #eachSetLayer = ceil(totalLayerNum/2) ;num_PlateLayer=2
    eachSetLayer = ceil(totalLayerNum/num_PlateLayer)   
    layerangles = [0,45,90,-45]
    #***********分割线
    i = 0 
    tempNum = 0
    iterNum = (totalLayerNum)/len(layerangles)
    tempstr1 = 'Ply-'+str(tempNum)
    while (i<iterNum):
            i = i+1
            j = 0
            while (j<len(layerangles)):
                tempNum = (i-1)*len(layerangles)+j+1
                tempstr1 = 'Ply-'+str(tempNum)
                if (tempNum%eachSetLayer==0):
                        tempstr2 = 'Set-LayerPla'+str(int(tempNum/eachSetLayer))         #/eachLayer=2
                else:
                        tempstr2 = 'Set-LayerPla'+str(int(tempNum/eachSetLayer)+1)
                #region = regionToolset.Region(cells=myPlatePart.sets[tempstr2].cells)
                region = myPlatePart.sets[tempstr2]
                compositeLayup.CompositePly(suppressed=False, plyName=tempstr1, region=region, 
                material='Laminate', thicknessType=SPECIFY_THICKNESS, 
                thickness=laythickness, orientationType=SPECIFY_ORIENT, orientationValue=layerangles[j], 
                additionalRotationType=ROTATION_NONE, additionalRotationField='', 
                axis=AXIS_3, angle=0.0, numIntPoints=1)
                j = j+1
    #***********分割线
    #创建Stringer铺层
    layupOrientation = myPlatePart.datums[Layup.id]
    compositeLayup = myPlatePart.CompositeLayup(
        name='Stringer', description='', elementType=SOLID, symmetric=False, 
        thicknessAssignment=FROM_SECTION)
    #***********分割线
    compositeLayup.ReferenceOrientation(orientationType=SYSTEM, 
        localCsys=layupOrientation, fieldName='', 
        additionalRotationType=ROTATION_NONE, angle=0.0, 
        additionalRotationField='', axis=AXIS_3, stackDirection=STACK_3)
    #***********分割线
    laythickness = 0.25
    #totalLayerNum = ceil(thickness/laythickness) ;thickness=4
    totalLayerNum = ceil(Sheight/laythickness)
    #eachSetLayer = ceil(totalLayerNum/2) ;num_PlateLayer=2
    eachSetLayer = ceil(totalLayerNum/num_StringerLayer)   
    layerangles = [0,45,90,-45]
    #***********分割线
    i = 0 
    tempNum = 0
    iterNum = (totalLayerNum)/len(layerangles)
    tempstr1 = 'Ply-'+str(tempNum)
    while (i<iterNum):
            i = i+1
            j = 0
            while (j<len(layerangles)):
                tempNum = (i-1)*len(layerangles)+j+1
                tempstr1 = 'Ply-'+str(tempNum)
                if (tempNum%eachSetLayer==0):
                        tempstr2 = 'Set-LayerStr'+str(int(tempNum/eachSetLayer))         #/eachLayer=2
                else:
                        tempstr2 = 'Set-LayerStr'+str(int(tempNum/eachSetLayer)+1)
                #region = regionToolset.Region(cells=myPlatePart.sets[tempstr2].cells)
                region = myPlatePart.sets[tempstr2]
                compositeLayup.CompositePly(suppressed=False, plyName=tempstr1, region=region, 
                material='Laminate', thicknessType=SPECIFY_THICKNESS, 
                thickness=laythickness, orientationType=SPECIFY_ORIENT, orientationValue=layerangles[j], 
                additionalRotationType=ROTATION_NONE, additionalRotationField='', 
                axis=AXIS_3, angle=0.0, numIntPoints=1)
                j = j+1
    #***********分割线
    #创建Frame铺层
    layupOrientation = myPlatePart.datums[Layup.id]
    compositeLayup = myPlatePart.CompositeLayup(
        name='Frame', description='', elementType=SOLID, symmetric=False, 
        thicknessAssignment=FROM_SECTION)
    #***********分割线
    compositeLayup.ReferenceOrientation(orientationType=SYSTEM, 
        localCsys=layupOrientation, fieldName='', 
        additionalRotationType=ROTATION_NONE, angle=0.0, 
        additionalRotationField='', axis=AXIS_3, stackDirection=STACK_3)
    #***********分割线
    laythickness = 0.25
    #totalLayerNum = ceil(thickness/laythickness) ;thickness=4
    totalLayerNum = ceil(Sheight/laythickness)
    #eachSetLayer = ceil(totalLayerNum/2) ;num_PlateLayer=2
    eachSetLayer = ceil(totalLayerNum/num_StringerLayer)   
    layerangles = [0,45,90,-45]
    #***********分割线
    i = 0 
    tempNum = 0
    iterNum = (totalLayerNum)/len(layerangles)
    tempstr1 = 'Ply-'+str(tempNum)
    while (i<iterNum):
            i = i+1
            j = 0
            while (j<len(layerangles)):
                tempNum = (i-1)*len(layerangles)+j+1
                tempstr1 = 'Ply-'+str(tempNum)
                if (tempNum%eachSetLayer==0):
                        tempstr2 = 'Set-LayerFra'+str(int(tempNum/eachSetLayer))         #/eachLayer=2
                else:
                        tempstr2 = 'Set-LayerFra'+str(int(tempNum/eachSetLayer)+1)
                #region = regionToolset.Region(cells=myPlatePart.sets[tempstr2].cells)
                region = myPlatePart.sets[tempstr2]
                compositeLayup.CompositePly(suppressed=False, plyName=tempstr1, region=region, 
                material='Laminate', thicknessType=SPECIFY_THICKNESS, 
                thickness=laythickness, orientationType=SPECIFY_ORIENT, orientationValue=layerangles[j], 
                additionalRotationType=ROTATION_NONE, additionalRotationField='', 
                axis=AXIS_3, angle=0.0, numIntPoints=1)
                j = j+1

#导入job模块
import job
#为模型创建并提交分析作业
jobName = 'stiffened-Plate-BuckleAnalysis'
myJob = mdb.Job(name=jobName, model = 'Stiffened_plate_solid', description='Plate Static Analysis')
#myJob.submit()