from __future__ import division
import FreeCAD as App
from PySide import QtGui
import numpy

from _tools import base_tool, input_field, text_field
from pivy_primitives_new_new import Container, Marker, coin, Line, COLORS
from . import BaseCommand

class Panel_Tool(BaseCommand):
    def GetResources(self):
        return {'Pixmap': 'panel_methode.svg', 'MenuText': 'panelmethode', 'ToolTip': 'panelmethode'}

    def tool(self, obj):
        return panel_tool(obj)

class panel_tool(base_tool):
    try:
        PPM = __import__("PPM")
        pan3d = __import__("PPM.pan3d", globals(), locals(), ["abc"], -1)
    except ImportError:
        PPM = None

    def __init__(self, obj):
        super(panel_tool, self).__init__(obj, widget_name="Properties", hide=True)
        if not self.PPM:
            self.QWarning = QtGui.QLabel("no panel_methode installed")
            self.layout.addWidget(self.QWarning)
        else:
            print(dir(self.PPM))
            self.case = None
            self.Qrun = QtGui.QPushButton("run")
            self.Qmidribs = QtGui.QSpinBox()
            self.Qprofile_points = QtGui.QSpinBox()
            self.Qstream_points = QtGui.QSpinBox()
            self.Qstream_radius = QtGui.QDoubleSpinBox()
            self.Qstream_interval = QtGui.QDoubleSpinBox()
            self.Qstream_num = QtGui.QSpinBox()
            self.Qmax_val = QtGui.QDoubleSpinBox()
            self.Qmin_val = QtGui.QDoubleSpinBox()
            self.cpc = Container()
            self.stream = coin.SoSeparator()
            self.glider_result = coin.SoSeparator()
            self.marker = Marker([[0, 0, 0]], dynamic=True)
            self.setup_widget()
            self.setup_pivy()

    def setup_widget(self):
        self.layout.setWidget(0, text_field, QtGui.QLabel("profile points"))
        self.layout.setWidget(0, input_field, self.Qprofile_points)
        self.layout.setWidget(1, text_field, QtGui.QLabel("midribs"))
        self.layout.setWidget(1, input_field, self.Qmidribs)
        self.layout.setWidget(2, text_field, QtGui.QLabel("number of streams"))
        self.layout.setWidget(2, input_field, self.Qstream_points)
        self.layout.setWidget(3, text_field, QtGui.QLabel("stream radius"))
        self.layout.setWidget(3, input_field, self.Qstream_radius)
        self.layout.setWidget(4, text_field, QtGui.QLabel("points per streamline"))
        self.layout.setWidget(4, input_field, self.Qstream_num)
        self.layout.setWidget(5, text_field, QtGui.QLabel("stream interval"))
        self.layout.setWidget(5, input_field, self.Qstream_interval)
        self.layout.setWidget(6, text_field, QtGui.QLabel("min_val"))
        self.layout.setWidget(6, input_field, self.Qmin_val)
        self.layout.setWidget(7, text_field, QtGui.QLabel("max_val"))
        self.layout.setWidget(7, input_field, self.Qmax_val)
        self.layout.addWidget(self.Qrun)

        self.Qmidribs.setMaximum(5)
        self.Qmidribs.setMinimum(0)
        self.Qmidribs.setValue(0)
        self.Qprofile_points.setMaximum(50)
        self.Qprofile_points.setMinimum(10)
        self.Qprofile_points.setValue(15)
        self.Qstream_points.setMaximum(30)
        self.Qstream_points.setMinimum(1)
        self.Qstream_points.setValue(5)
        self.Qstream_radius.setMaximum(2)
        self.Qstream_radius.setMinimum(0)
        self.Qstream_radius.setValue(0.3)
        self.Qstream_radius.setSingleStep(0.1)
        self.Qstream_interval.setMaximum(1.000)
        self.Qstream_interval.setMinimum(0.00001)
        self.Qstream_interval.setValue(0.1)
        self.Qstream_interval.setSingleStep(0.01)

        self.Qstream_num.setMaximum(300)
        self.Qstream_num.setMinimum(5)
        self.Qstream_num.setValue(20)

        self.Qmin_val.setMaximum(3)
        self.Qmin_val.setMinimum(-10)
        self.Qmin_val.setValue(-3)
        self.Qmin_val.setSingleStep(0.01)

        self.Qmax_val.setMaximum(10)
        self.Qmax_val.setMinimum(1)
        self.Qmax_val.setValue(1)
        self.Qmax_val.setSingleStep(0.01)


        self.Qstream_points.valueChanged.connect(self.update_stream)
        self.Qstream_radius.valueChanged.connect(self.update_stream)
        self.Qstream_interval.valueChanged.connect(self.update_stream)
        self.Qstream_num.valueChanged.connect(self.update_stream)

        self.Qmin_val.valueChanged.connect(self.show_glider)
        self.Qmax_val.valueChanged.connect(self.show_glider)

        self.Qrun.clicked.connect(self.run)

    def setup_pivy(self):
        self.cpc.register(self.view)
        self.task_separator.addChild(self.cpc)
        self.task_separator.addChild(self.stream)
        self.task_separator.addChild(self.glider_result)
        self.cpc.addChild(self.marker)
        self.marker.on_drag_release.append(self.update_stream)
        self.marker.on_drag.append(self.update_stream_fast)

    def update_stream(self):
        self.stream.removeAllChildren()
        if self.case:
            point = list(self.marker.points[0].getValue())
            points = numpy.random.random((self.Qstream_points.value(), 3)) - numpy.array([0.5, 0.5, 0.5])
            points *= self.Qstream_radius.value()
            points += numpy.array(point)
            points = points.tolist()
            for p in points:
                pts = self.stream_line(p, self.Qstream_interval.value(), self.Qstream_num.value())
                self.stream.addChild(Line(pts, dynamic=False))

    def update_stream_fast(self):
        self.stream.removeAllChildren()
        if self.case:
            point = list(self.marker.points[0].getValue())
            pts = self.stream_line(point, 0.05, 20)
            self.stream.addChild(Line(pts, dynamic=False))

    def update_glider(self):
        self.obj.ViewObject.num_ribs = self.Qmidribs.value()
        self.obj.ViewObject.profile_num = self.Qprofile_points.value()

    def stream_line(self, point, interval, numpoints):
        flow_path = self.case.flow_path(self.PPM.Vector3(*point), interval, numpoints)
        return [[p.x, p.y, p.z] for p in flow_path.values]

    def create_panels(self, midribs=0, profile_numpoints=10):
        glider = self.obj.glider_instance.copy_complete()
        glider.profile_numpoints = profile_numpoints
        ribs = glider.return_ribs(midribs)

        # deleting the last vertex of every rib (no trailing edge gap)
        ribs = [rib[:-1] for rib in ribs]

        # get a numbered representation + flatten vertices
        i = 0
        vertices = [] 
        ribs_new = []
        for rib in ribs:
            rib_new = []
            for vertex in rib:
                rib_new.append(i)
                vertices.append(vertex)
                i += 1
            rib_new.append(rib_new[0])
            ribs_new.append(rib_new)
        ribs = ribs_new
        wake_edge = [rib[0] for rib in ribs]
        polygons = []
        for i, rib_i in enumerate(ribs[:-1]):
            rib_j = ribs[i+1]
            for k, _ in enumerate(rib_j[:-1]):
                l = k + 1
                p = [rib_i[k], rib_j[k], rib_j[l], rib_i[l]]
                polygons.append(p)

    # Panel3-methode
        self._vertices = [self.PPM.PanelVector3(*vertex) for vertex in vertices]
        self._panels = [self.PPM.Panel3([self._vertices[nr] for nr in pol]) for pol in polygons]
        _wake_edges = [self._vertices[i] for i in wake_edge]

        self.case.panels = self._panels
        self.case.wake_edges = _wake_edges

    def run(self):
        self.update_glider()
        self.case = self.pan3d.DirichletDoublet0Source0Case3()
        alpha = numpy.arctan(1 / self.glider_2d.glide)
        speed = self.glider_2d.speed
        self.case.vinf = self.PPM.Vector3(speed * numpy.cos(alpha) , 0, speed * numpy.sin(alpha))
        self.create_panels(self.Qmidribs.value(), self.Qprofile_points.value())
        self.case.farfield = 1000000
        self.case.create_wake(20, 20)
        self.case.run()
        self.show_glider()

    def show_glider(self):
        self.glider_result.removeAllChildren()
        verts = []
        pols = []
        cols = []
        index = 0
        for pan in self._panels:
            for vert in pan.points:
                verts.append(list(vert))
                pols.append(index)
                index += 1
            cols.append(pan.cp)
            pols.append(-1)     # end of pol
        vertex_property = coin.SoVertexProperty()
        face_set = coin.SoIndexedFaceSet()
        for i, col in enumerate(cols):
            vertex_property.orderedRGBA.set1Value(i, coin.SbColor(self.color(col)).getPackedValue())
            vertex_property.materialBinding = coin.SoMaterialBinding.PER_FACE
        vertex_property.vertex.setValues(0, len(verts), verts)
        face_set.coordIndex.setValues(0, len(pols), pols)
        self.glider_result.addChild(vertex_property)
        self.glider_result.addChild(face_set)
        p1 = numpy.array(list(self.case.pressure_point))
        f = numpy.array(list(self.case.force))
        line = Line([p1, p1 + f])
        self.glider_result.addChild(line)

    def color(self, value):
        def f(n, i, x):
            if ((i - 1) / n) < x < (i / n):
                return (n * x + 1 - i)
            elif (i / n) <= x < ((i + 1) / n):
                return  (- n * x + 1 + i)
            else:
                return 0
        max_val=self.Qmax_val.value()
        min_val=self.Qmin_val.value()
        red = numpy.array(COLORS["red"])
        blue = numpy.array(COLORS["blue"])
        yellow = numpy.array(COLORS["yellow"])
        white = numpy.array(COLORS["white"])
        norm_val = (value - min_val) / (max_val - min_val)
        return list(f(3, 0, norm_val) * red + f(3,1,norm_val) * yellow + f(3,2,norm_val) * white + f(3,3,norm_val) * blue)