from __future__ import division
import sys
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from PyQt4 import QtGui, QtCore
from openglider.vector import norm_squared


class MplWidget(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100, dynamic=True):
        self.cid_id = None
        self.elements = []

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        self.ax.axis("equal")

        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.setParent(parent)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setFocus()
        if dynamic:
            self.fig.canvas.mpl_connect('button_press_event', self.onclick)
            self.fig.canvas.mpl_connect('button_release_event', self.offclick)
            self.fig.canvas.mpl_connect('scroll_event', self.zoom)

    def updatedata(self, i=None):
        if not i is None:
            elements = [self.elements[i]]
        else:
            elements = self.elements
        for element, subplot, plot in elements:
            plot.set_xdata(element.x_list)
            plot.set_ydata(element.y_list)

    @property
    def pixel_scale(self):
        x_bounds = self.ax.get_xlim()
        return (x_bounds[1]-x_bounds[0])/get_ax_size(self.ax, self.fig)[0]

    def onclick(self, event):
        """
        1: find point (test if the point lies in the drag circle)
            if more than one point is selected take the first
        2: test if point is draggable, only one direction or not draggable
        3: give new position and repaint as long as mouse is pressed

        advanced:
            show which point mouse is over
            if ctrl is pressed:
                snap to grid +  show grid
            if shift is pressed
                snap to other point values
            doublepress:
                enter value for x and y
        """
        if event.xdata is None or event.ydata is None:
            return
        elif event.button == 3:
            startpos = (event.x, event.y)
            self.cid_id = self.fig.canvas.mpl_connect('motion_notify_event', self._move(startpos=startpos))

        elif event.button == 1:
            for (element, __, __) in self.elements:
                for i, (x, y) in enumerate(element.control_points):
                    if norm_squared([x-event.xdata, y-event.ydata]) < (1 * self.pixel_scale):
                        self.cid_id = self.fig.canvas.mpl_connect('motion_notify_event', self._drag(element, i))
                        return
        else:
            self.cid_id = None

    def _drag(self, element, point_id=0):
        def __drag(event):
            if not (event.xdata is None and event.ydata is None):
                element.x_list[point_id] = event.xdata
                element.y_list[point_id] = event.ydata
            self.updatedata()
            self.fig.canvas.draw()
        return __drag

    def _move(self, startpos):
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()

        def __move(event):
            delta_x = (startpos[0]-event.x)/self.fig.dpi
            delta_y = (startpos[1]-event.y)/self.fig.dpi
            self.ax.set_xlim([current_xlim[0]+delta_x, current_xlim[1]+delta_x])
            self.ax.set_ylim([current_ylim[0]+delta_y, current_ylim[1]+delta_y])
            self.fig.canvas.draw()
        return __move

    def offclick(self, event):
        if not self.cid_id is None:
            self.fig.canvas.mpl_disconnect(self.cid_id)

    def zoom(self, event):
        if event.button == "down":
            factor = 0.05
        else:
            factor = -0.05
        if event.key == 'control':
            factor *= 10
        factor += 1
        curr_xlim = self.ax.get_xlim()
        curr_ylim = self.ax.get_ylim()

        new_width = (curr_xlim[1]-curr_xlim[0])*factor

        relx = (curr_xlim[1]-event.xdata)/(curr_xlim[1]-curr_xlim[0])
        rely = (curr_ylim[1]-event.ydata)/(curr_ylim[1]-curr_ylim[0])
        self.ax.set_xlim([event.xdata-new_width*(1-relx),
                          event.xdata+new_width*relx])
        self.ax.set_ylim([event.ydata-new_width*(1-rely)/2,
                          event.ydata+new_width*rely/2])
        self.fig.canvas.draw()


class Line():
    def __init__(self, x_list, y_list, line_width=1, mplwidget=None):
        self.mpl = []
        self.linewidth = line_width
        self.x_list = x_list
        self.y_list = y_list
        if mplwidget is not None:
            self.insert_mpl(mplwidget)
        self.drag_pos = 0

    def insert_mpl(self, *mpl_widgets):
        for widget in mpl_widgets:
            subplot = widget.fig.add_subplot(1, 1, 1)
            subplot.axis("equal")
            subplot.get_xaxis().set_visible(False)
            subplot.get_yaxis().set_visible(False)
            subplotplot, = subplot.plot([], [], lw=self.linewidth, color='black', ms=5, marker="o", mfc="r", picker=5)
            widget.elements.append([self, subplot, subplotplot])
            widget.updatedata(-1)
            subplot.relim()
            subplot.autoscale_view()

    @property
    def control_points(self):
        return zip(self.x_list, self.y_list)

    @control_points.setter
    def control_points(self, points):
        self.x_list = points[:, 0]
        self.y_list = points[:, 1]


class BezierCurve:
    def __init__(self):
        pass


def get_ax_size(ax, fig):
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    width = bbox.width * fig.dpi
    height = bbox.height * fig.dpi
    return width, height



"""
- by pressing ctrl + space the actual widget -> fullscreen
"""


class ApplicationWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle("application main window")
        self.mainwidget = QtGui.QWidget(self)

        self.splitter = QtGui.QSplitter(self.mainwidget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)

        mpl1 = MplWidget(QtGui.QWidget(self.mainwidget), width=5, height=4, dpi=100, dynamic=True)
        mpl2 = MplWidget(QtGui.QWidget(self.mainwidget), width=5, height=4, dpi=100, dynamic=True)

        line1 = Line([1, 2, 3, 5, 6], [1, 2, 1, 3, 4], line_width=0, mplwidget=mpl1)
        line2 = Line([2, 3, 4, 2], [2, 3, 1, 0], mplwidget=mpl1)
        line3 = Line([1, 1, 1], [2, 3, 1], mplwidget=mpl2)
        line1.insert_mpl(mpl2)
        mpl1.updatedata()
        mpl2.updatedata()

        self.splitter.addWidget(mpl1)
        self.splitter.addWidget(mpl2)

        self.vertikal_layout = QtGui.QVBoxLayout(self.mainwidget)
        self.vertikal_layout.addWidget(self.splitter)
        self.setCentralWidget(self.mainwidget)


if __name__ == "__main__":
    qApp = QtGui.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.show()
    sys.exit(qApp.exec_())