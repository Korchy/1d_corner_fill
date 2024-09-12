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

    _err_steps = 25

    @classmethod
    def fill(cls, context, op, obj):
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

            # print('ready bridges', 'step ', steps)
            # for bridge in bridges:
            #     print([v.index for v in bridge])

            # get corner (selected on this step) vertices
            corner_vertices = set(itertools.chain.from_iterable((bridge[0], bridge[-1]) for bridge in bridges))

            # print('conner vertices')
            # print([v.index for v in corner_vertices])

            # deselect all selected vertices - will select new vertices when processing this step
            cls._deselect(bm=bm, faces=True, edges=True, vertices=True)
            # create new face on each corner vertex
            for vertex in corner_vertices:

                # print('vertex', vertex.index)

                # get 3 vertices based on corner vertex and create a face
                link_bridges = [bridge for bridge in bridges if vertex in (bridge[0], bridge[-1])]

                # print('link bridges')
                # for lb in link_bridges:
                #     print([_v.index for _v in lb])

                # process only if this vertex has two linked bridges
                #   filter if there is only one bridge between two vertices
                if len(link_bridges) == 2:
                    v1 = link_bridges[0][1] if link_bridges[0][0] == vertex else link_bridges[0][-2]
                    v2 = link_bridges[1][1] if link_bridges[1][0] == vertex else link_bridges[1][-2]

                    # print('vertex, v1, v2')
                    # print(vertex.index, v1.index, v2.index)

                    # create face on corner vertex
                    new_vertex, new_face = cls._face_from_vert(bm=bm, v0=vertex, v1=v1, v2=v2)
                    # select new corner vertex for building new bridges on the next step
                    new_vertex.select = True
                    # replace old corner vertex in brides with new one
                    for bridge in bridges:
                        bridge[0] = new_vertex if bridge[0] == vertex else bridge[0]
                        bridge[-1] = new_vertex if bridge[-1] == vertex else bridge[-1]
            # create faces loops by bridges
            for bridge in bridges:
                # all corner vertices on the bridge must be already processed
                if bridge[0].index == -1 and bridge[-1].index == -1:
                    cls._face_loop_by_bridge(bm=bm, bridge=bridge)
            # update indices not to have index = -1 on the next step
            bm.verts.index_update()

            # print('modified bridges', 'step ', steps)
            # for bridge in bridges:
            #     print([v.index for v in bridge])

            # cycling control
            if steps >= cls._err_steps:
                print('ERR: Broking on max steps, maybe cycling. Steps: ', steps)
                break
            # rebuild bridges for next step
            bridges = cls._vertices_bridges(bm=bm)

        # err warning
        if steps >= cls._err_steps:
            op.report({'INFO'}, 'ERR: Interrupted on max available steps (' + str(steps) + ')')
        else:
            op.report({'INFO'}, 'OK: Processed with ' + str(steps) + ' steps')
        # recalculate normals
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
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

        # print('possible_bridges_starts')
        # print(set(bs[0].index for bs in possible_bridges_starts))

        # for each start point of possible bridge - built full bridge
        max_bridge_len = len(bm.verts)
        for bridge in possible_bridges_starts:
            # follow for the next vertices until it ends on another selected vertex or free vertex (drop bridge)
            if cls._build_bridge(bridge=bridge, max_steps=max_bridge_len):
                # print(bridge)
                if [bridge[-1], bridge[0]] not in [[br[0], br[-1]] for br in bridges] \
                        and len(bridge) > 3:
                    # don't add same bridges - if first-last vertices of one are last-first vertices of another
                    # don't add bridge with 3 and less vertices (no improvements on next step)
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
        # create 4-th vertex for face
        v3_co = v0.co + ((v1.co - v0.co) + (v2.co - v0.co))
        v3 = bm.verts.new(v3_co)
        # create face from all 4 vertices
        face = bm.faces.new((v0, v2, v3, v1))
        return v3, face

    @classmethod
    def _face_loop_by_bridge(cls, bm, bridge):
        # create face loop by vertices bridge (list of vertices)
        v0 = bridge[0]
        last_vertex = bridge[-1]
        chunks = list(cls._chunks(lst=bridge[1:-1], n=2, offset=1))[:-1]

        # print('bridge')
        # print(bridge)
        # print('chunks')
        # print(list(chunks))

        average_vector_co = ((v0.co - bridge[1].co) + (last_vertex.co - bridge[-2].co)) / 2

        for chunk in chunks:
            # create 4-th vertex
            if chunk == chunks[-1]:
                # for the last chunk, use last vertex instead creating new
                v3 = last_vertex
            else:
                # v3 = bm.verts.new(chunk[1].co - chunk[1].normal * average_vector_co.length)
                v3 = bm.verts.new(chunk[1].co + average_vector_co)
            # create face from all 4 vertices
            bm.faces.new((v0, chunk[0], chunk[1], v3))
            # for next chunk, new v3 vertex will be the first v0 vertex
            v0 = v3

    @staticmethod
    def _deselect(bm, faces=False, edges=False, vertices=False):
        # remove all selection on bmesh
        if faces:
            for face in bm.faces:
                face.select = False
        if edges:
            for edge in bm.edges:
                edge.select = False
        if vertices:
            for vertex in bm.verts:
                vertex.select = False

    @staticmethod
    def _chunks(lst, n, offset=0):
        for i in range(0, len(lst), n - offset):
            yield lst[i:i + n]

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
            op=self,
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
