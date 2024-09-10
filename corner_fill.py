# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_corner_fill

import bpy
import bmesh
from bpy.types import Operator, Panel
from bpy.utils import register_class, unregister_class
import itertools

bl_info = {
    "name": "Corner Fill",
    "description": "Fill closed vertices loop with polygons loop starting from selected vertices",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > OBJ Tools",
    "doc_url": "https://github.com/Korchy/1d_corner_fill",
    "tracker_url": "https://github.com/Korchy/1d_corner_fill",
    "category": "All"
}


# MAIN CLASS

class CornerFill:

    _err_steps = 3

    @classmethod
    def fill(cls, context, obj):
        # fills closed vertices loop with polygons loops starting from selected vertices
        # current mode
        mode = obj.mode
        # switch to OBJECT mode
        if obj.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # process current object
        # mesh to bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        # get all bridges between selected vertices
        bridges = cls._vertices_bridges(bm=bm)
        steps = 0
        # try to process step by step until new bridges couldn't be created
        while bridges:
            steps += 1

            print('ready bridges', 'step ', steps)
            for bridge in bridges:
                print([v.index for v in bridge])

            # get corner vertices
            corner_vertices = set(itertools.chain.from_iterable((bridge[0], bridge[-1]) for bridge in bridges))
            # print([v.index for v in corner_vertices])

            for vertex in corner_vertices:
                # get 3 vertices based on corner vertex to create a face
                link_bridges = [bridge for bridge in bridges if vertex in (bridge[0],bridge[-1])]
                v1 = link_bridges[0][1] if link_bridges[0][0] == vertex else link_bridges[0][-2]
                v2 = link_bridges[1][1] if link_bridges[1][0] == vertex else link_bridges[1][-2]
                cls._face_from_vert(bm=bm, v0=vertex, v1=v1, v2=v2)


            # for bridge in bridges:
            #     # get first vertex (currently selected) and try to create face
            #     pass


            # cycling control
            if steps >= cls._err_steps:
                print('ERR processing mesh. Maybe cycling. Steps: ', steps)
                break
            # rebuild bridges for next step
            bridges = cls._vertices_bridges(bm=bm)

        # save changed data to mesh
        bm.to_mesh(obj.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @classmethod
    def _vertices_bridges(cls, bm):
        # get all vertices bridges between selected vertices
        bridges = []
        # for each selected vertex get all bridges started from it and following on clear edges
        possible_bridges_starts = [[vertex, edge.other_vert(vertex)] \
                            for vertex in bm.verts if vertex.select \
                            for edge in vertex.link_edges if len(edge.link_faces) <= 1 \
                                   and not edge.other_vert(vertex).select]      # two selected vertices near each other
        # for each start point of possible bridge - built full bridge
        max_bridge_len = len(bm.verts)
        for bridge in possible_bridges_starts:
            # follow for the next vertices until it ends on another selected vertex or free vertex (drop bridge)
            if cls._build_bridge(bridge=bridge, max_steps=max_bridge_len):
                if [bridge[-1], bridge[0]] not in [[br[0], br[-1]] for br in bridges]:
                    # don't add same bridges - if first-last vertices of one are last-first vertices of another
                    bridges.append(bridge)

        return bridges

    @classmethod
    def _build_bridge(cls, bridge, max_steps=0):
        # build bridge from its end vertex until it ends on selected vertex or can't continue (free vertex, fork, etc.)
        next_vertex = cls._next_vert(vertex=bridge[1], bridge=bridge)
        while next_vertex:
            bridge.append(next_vertex)
            if next_vertex.select:
                # moved to another selected vertex - OK (end of the bridge)
                return True
            next_vertex = cls._next_vert(next_vertex, bridge)
            if len(bridge) > max_steps:
                # Err
                print('ERR building bridge between two selected vertices. Starts with:', bridge[:2])
                return False
        # Err if we ends bridge not by another selected vertex
        return False

    @staticmethod
    def _next_vert(vertex, bridge):
        # get next vertex for bridge starting from vertex
        possible_next_edges = [edge for edge in vertex.link_edges \
                               if len(edge.link_faces) <= 1 \
                               and edge.other_vert(vertex) not in bridge]
        if len(possible_next_edges) == 1:
            next_edge = next(iter(possible_next_edges), None)
            if next_edge:
                next_vertex = next_edge.other_vert(vertex)
                return next_vertex

    @staticmethod
    def _face_from_vert(bm, v0, v1, v2):
        # create face from vertex
        # create last vertex
        v3_co = v0.co + ((v1.co - v0.co) + (v2.co - v0.co))
        v3 = bm.verts.new(v3_co)
        # create face from all four vertices
        bm.faces.new((v0, v2, v3, v1))


    @staticmethod
    def ui(layout, context):
        # ui panel
        layout.operator(
            operator='corner_fill.fill',
            icon='SURFACE_NCIRCLE'
        )


# OPERATORS

class CornerFill_OT_fill(Operator):
    bl_idname = 'corner_fill.fill'
    bl_label = 'Corner Fill'
    bl_description = 'Fill from corners'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        CornerFill.fill(
            context=context,
            obj=context.object
        )
        return {'FINISHED'}


# PANELS

class CornerFill_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Corner Fill"
    bl_category = '1D'

    def draw(self, context):
        CornerFill.ui(
            layout=self.layout,
            context=context
        )


# REGISTER

def register(ui=True):
    register_class(CornerFill_OT_fill)
    if ui:
        register_class(CornerFill_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(CornerFill_PT_panel)
    unregister_class(CornerFill_OT_fill)


if __name__ == "__main__":
    register()
