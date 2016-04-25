import numpy as np
import bpy
import bgl
from bpy.props import FloatVectorProperty, IntProperty, EnumProperty

bl_info = {
    "name": "Paint Tools",
    "author": "Nutti",
    "version": (1, 0),
    "blender": (2, 77, 0),
    "location": "Image Editor > Paint Tools",
    "description": "Paint Tools for Blender",
    "warning": "",
    "support": "COMMUNITY",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Paint"
}


def runnable(context):
    is_edit_mode = (context.mode == 'EDIT_MESH')
    area, region, space = get_space('IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', context)
    is_paint_mode = (space.mode == 'PAINT')

    return is_edit_mode and not is_paint_mode


def redraw_all_areas():
    for area in bpy.context.screen.areas:
        area.tag_redraw()


def get_space(area_type, region_type, space_type, context):
    for area in context.screen.areas:
        if area.type == area_type:
            break
    for region in area.regions:
        if region.type == region_type:
            break
    for space in area.spaces:
        if space.type == space_type:
            break

    return (area, region, space)


def get_active_image():
    area, region, space = get_space('IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', bpy.context)
    return area.spaces.active.image


def to_pixel(context, mvx, mvy):
    mrx, mry = context.region.view2d.region_to_view(mvx, mvy)
    img = get_active_image()
    mpx = img.size[0] * mrx
    mpy = img.size[1] * mry
    return (int(mpx), int(mpy))


def get_img_info(context):
    scene = context.scene
    props = scene.pt_props
    img = get_active_image()

    info = {}
    info['image'] = img
    info['pixels'] = np.array(img.pixels[:])
    info['num_pixels'] = int(len(img.pixels) / 4)
    info['width'] = img.size[0]
    info['height'] = img.size[0]

    return info


def get_pixel_rect_bb(context):
    scene = context.scene
    props = scene.pt_props
    xs, ys = to_pixel(context, props.start[0], props.start[1])
    xe, ye = to_pixel(context, props.end[0], props.end[1])
    y0 = min(ys, ye) + 1
    y1 = max(ys, ye) + 1
    x0 = min(xs, xe)
    x1 = max(xs, xe)
     
    return {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}


class PT_FillRect(bpy.types.Operator):

    bl_idname = "paint.pt_fill_rect"
    bl_label = "Fill Rect"
    bl_description = "Fill Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __fill_rect(self, img, rect, color):
        x0 = rect['x0']
        y0 = rect['y0']
        x1 = rect['x1']
        y1 = rect['y1']
        pixels = img['pixels']
        w = img['width']

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + (x + x0)) * 4
                pixels[offset] = color[0]
                pixels[offset + 1] = color[1]
                pixels[offset + 2] = color[2]
                pixels[offset + 3] = 1.0

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__fill_rect(img, rect, context.scene.pt_fill_color)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_EraseRect(bpy.types.Operator):

    bl_idname = "paint.pt_erase_rect"
    bl_label = "Erase Rect"
    bl_description = "Erase Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __erase_rect(self, img, rect):
        x0 = rect['x0']
        y0 = rect['y0']
        x1 = rect['x1']
        y1 = rect['y1']
        pixels = img['pixels']
        w = img['width']

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + (x + x0)) * 4
                pixels[offset] = 0.0
                pixels[offset + 1] = 0.0
                pixels[offset + 2] = 0.0
                pixels[offset + 3] = 0.0

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__erase_rect(img, rect)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_SelectAll(bpy.types.Operator):

    bl_idname = "paint.pt_select_all"
    bl_label = "Select All"
    bl_description = "Select all"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.pt_props

        props.start = context.region.view2d.view_to_region(0.0, 0.0)
        props.end = context.region.view2d.view_to_region(1.0, 1.0)

        redraw_all_areas()

        return {'FINISHED'}



class PT_BinarizeRect(bpy.types.Operator):

    bl_idname = "paint.pt_binarize_rect"
    bl_label = "Binarize Rect"
    bl_description = "Binarize Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __binarize_rect(self, img, rect, threshold, color):
        x0 = rect['x0']
        y0 = rect['y0']
        x1 = rect['x1']
        y1 = rect['y1']
        pixels = img['pixels']
        w = img['width']
        t = threshold / 255.0

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + (x + x0)) * 4
                fill_black = True
                if color == 'RED' and (pixels[offset] > t):
                    fill_black = False
                if color == 'GREEN' and (pixels[offset + 1] > t):
                    fill_black = False
                if color == 'BLUE' and (pixels[offset + 2] > t):
                    fill_black = False

                if fill_black:
                    pixels[offset] = 0.0
                    pixels[offset + 1] = 0.0
                    pixels[offset + 2] = 0.0
                else:
                    pixels[offset] = 1.0
                    pixels[offset + 1] = 1.0
                    pixels[offset + 2] = 1.0

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__binarize_rect(
            img, rect, context.scene.pt_binarize_threshold,
            context.scene.pt_binarize_threshold_color)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_BoxRenderer(bpy.types.Operator):

    bl_idname = "paint.pt_box_renderer"
    bl_label = "Box Renderer"
    bl_description = "Bounding Box Renderer in Image Editor"

    __handle = None

    @staticmethod
    def handle_add(self, context):
        if PT_BoxRenderer.__handle is None:
            PT_BoxRenderer.__handle = bpy.types.SpaceImageEditor.draw_handler_add(
                PT_BoxRenderer.draw_bb,
                (self, context), "WINDOW", "POST_PIXEL")

    @staticmethod
    def handle_remove(self, context):
        if PT_BoxRenderer.__handle is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(
                PT_BoxRenderer.__handle, "WINDOW")
            PT_BoxRenderer.__handle = None

    @staticmethod
    def draw_bb(self, context):
        props = context.scene.pt_props
        x0, y0 = props.start
        x1, y1 = props.end

        verts = [
            [x0, y0],
            [x0, y1],
            [x1, y1],
            [x1, y0]
        ]

        bgl.glLineWidth(1)
        bgl.glBegin(bgl.GL_LINE_LOOP)
        bgl.glColor4f(1.0, 1.0, 1.0, 1.0)
        for (x, y) in verts:
            bgl.glVertex2f(x, y)
        bgl.glEnd()

    def __get_mouse_position(self, context, event):
        mx, my = event.mouse_region_x, event.mouse_region_y
        min_x, min_y = context.region.view2d.view_to_region(0.0, 0.0)
        max_x, max_y = context.region.view2d.view_to_region(1.0, 1.0)
        if mx < min_x:
            mx = min_x
        elif mx > max_x:
            mx = max_x
        if my < min_y:
            my = min_y
        elif my > max_y:
            my = max_y

        return (mx, my)

    def modal(self, context, event):
        props = context.scene.pt_props
        redraw_all_areas()
        mx, my = self.__get_mouse_position(context, event)
        if props.running is False or not runnable(context):
            props.start = (mx, my)
            props.end = props.start
            PT_BoxRenderer.handle_remove(self, context)
            props.running = False
            return {'FINISHED'}

        if event.type == 'LEFTMOUSE':
            if not props.selecting and event.value == 'PRESS':
                area, region, space = get_space(
                    'IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', context)
                out = False
                if region.width < event.mouse_region_x:
                    out = True
                if event.mouse_region_x < 0:
                    out = True
                if region.height < event.mouse_region_y:
                    out = True
                if region.height < 0:
                    out = True
                if not out:
                    props.selecting = True
                    props.start = (mx, my)
                    props.end = props.start
            elif props.selecting and event.value == 'RELEASE':
                props.selecting = False
                props.end = (mx, my)
        if event.type == 'MOUSEMOVE':
            if props.selecting:
                props.end = (mx, my)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        props = context.scene.pt_props
        if props.running is False:
            PT_BoxRenderer.handle_add(self, context)
            context.window_manager.modal_handler_add(self)
            props.running = True
            props.selecting = False
            return {'RUNNING_MODAL'}
        else:
            props.running = False
        return {'FINISHED'}


class IMAGE_PT_PT(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_label = 'Painting Tool'

    @classmethod
    def poll(cls, context):
        return runnable(context)

    def draw(self, context):
        sc = context.scene
        props = sc.pt_props
        layout = self.layout
        layout.label(text="", icon='PLUGIN')
        layout.label(text="Rectangular Selection")
        if props.running == False:
            layout.operator(PT_BoxRenderer.bl_idname, text="", icon='PLAY')
        else:
            layout.operator(PT_BoxRenderer.bl_idname, text="", icon='PAUSE')

            col = layout.column()
            col.operator(PT_SelectAll.bl_idname, text="Select All")

            split = layout.split()
            col = split.column()
            col.operator(PT_FillRect.bl_idname, text="Fill")
            col = split.column()
            col.prop(sc, "pt_fill_color", text="")

            col = layout.column()
            col.operator(PT_EraseRect.bl_idname, text="Erase")

            col = layout.column()
            col.operator(PT_BinarizeRect.bl_idname, text="Binarize")
            split = layout.split()
            col = split.column()
            col.prop(sc, "pt_binarize_threshold", text="")
            col = split.column()
            col.prop(sc, "pt_binarize_threshold_color", text="")


class PTProps():
    running = False
    selecting = False
    start = (0.0, 0.0)
    end = (0.0, 0.0)

def init_props():
    scene = bpy.types.Scene
    scene.pt_props = PTProps()
    scene.pt_fill_color = FloatVectorProperty(
        name="Fill Color",
        description="Filled by this color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0)
    scene.pt_binarize_threshold_color = EnumProperty(
        name="Threshold Color",
        description="Binarize Threshold Color",
        items=[
            ('RED', "Red", "Red"),
            ('GREEN', "Green", "Green"),
            ('BLUE', "Blue", "Blue")],
        default='RED')
    scene.pt_binarize_threshold = IntProperty(
        name="Threshold",
        description="Binarize Threshold",
        default=128,
        min=0,
        max=255)

def clear_props():
    scene = bpy.types.Scene
    del scene.pt_fill_color
    del scene.pt_props
    del scene.pt_binarize_threshold
    del scene.pt_binarize_threshold_color

def register():
    bpy.utils.register_module(__name__)
    init_props()

def unregister():
    bpy.utils.unregister_module(__name__)
    clear_props()

if __name__ == "__main__":
    register()

