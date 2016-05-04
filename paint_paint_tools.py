import numpy as np
import bpy
import bgl
from bpy.props import FloatProperty, FloatVectorProperty, IntProperty, EnumProperty
from math import pow


bl_info = {
    "name": "Paint Tools",
    "author": "Nutti, chromoly",
    "version": (1, 0),
    "blender": (2, 77, 0),
    "location": "Image Editor > Paint Tools",
    "description": "Paint Tools for Blender",
    "warning": "",
    "support": "COMMUNITY",
    "wiki_url": "https://github.com/nutti/Paint-Tools",
    "tracker_url": "https://github.com/nutti/Paint-Tools/issues",
    "category": "Paint"
}


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


def get_active_image(context):
    if context.area and context.area.type == 'IAMGE_EDITOR':
        image = context.area.spaces.active.image
        if image:
            return image
    area, region, space = get_space('IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', bpy.context)
    return area.spaces.active.image


def to_pixel(context, mvx, mvy):
    mrx, mry = context.region.view2d.region_to_view(mvx, mvy)
    img = get_active_image(context)
    mpx = img.size[0] * mrx
    mpy = img.size[1] * mry
    return (int(mpx), int(mpy))


def get_img_info(context):
    scene = context.scene
    props = scene.pt_props
    img = get_active_image(context)

    info = {}
    info['image'] = img
    info['pixels'] = np.array(img.pixels[:])
    info['num_pixels'] = int(len(img.pixels) / 4)
    info['width'] = img.size[0]
    info['height'] = img.size[1]

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
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']

        pixels = img['pixels'].reshape((h, w, 4))
        pixels[y0:y1, x0:x1] = [*color[:3], 1.0]

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)

        self.__fill_rect(img, rect, context.scene.pt_fill_color)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_CopyRect(bpy.types.Operator):

    bl_idname = "paint.pt_copy_rect"
    bl_label = "Copy Rect"
    bl_description = "Copy Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __copy_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']

        pixels = img['pixels'].reshape((h, w, 4))

        info = {}
        info['pixels'] = pixels[y0:y1, x0:x1].copy()
        info['width'] = x1 - x0
        info['height'] = y1 - y0

        return info

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)

        context.scene.pt_props.copied_pixels = self.__copy_rect(img, rect)

        return {'FINISHED'}


class PT_CutRect(bpy.types.Operator):

    bl_idname = "paint.pt_cut_rect"
    bl_label = "Cut Rect"
    bl_description = "Cut Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __cut_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']

        pixels = img['pixels'].reshape((h, w, 4))

        info = {}
        info['pixels'] = pixels[y0:y1, x0:x1].copy()
        info['width'] = x1 - x0
        info['height'] = y1 - y0

        pixels[y0:y1, x0:x1] = 0.0

        return info

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)

        context.scene.pt_props.copied_pixels = self.__cut_rect(img, rect)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_PasteRect(bpy.types.Operator):

    bl_idname = "paint.pt_paste_rect"
    bl_label = "Paste Rect"
    bl_description = "Paste Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __paste_rect(self, img, p, copied):
        x0 = int(p[0])
        x1 = int(p[0]) + copied['width']
        y0 = int(p[1]) - copied['height']
        y1 = int(p[1])
        w = img['width']
        h = img['height']

        pixels = img['pixels'].reshape((h, w, 4))
        pixels[y0:y1, x0:x1] = copied['pixels']

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__paste_rect(
            img, (rect['x0'], rect['y1']), context.scene.pt_props.copied_pixels)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_EraseRect(bpy.types.Operator):

    bl_idname = "paint.pt_erase_rect"
    bl_label = "Erase Rect"
    bl_description = "Erase Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __erase_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']

        pixels = img['pixels'].reshape((h, w, 4))
        pixels[y0:y1, x0:x1] = 0.0

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
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']

        pixels = img['pixels'].reshape((h, w, 4))
        t = threshold / 255.0

        pixels_rect = pixels[y0:y1, x0:x1]
        i = ['RED', 'GREEN', 'BLUE'].index(color)
        fill_black = pixels_rect[:, :, i] < t
        fill_white = pixels_rect[:, :, i] > t
        pixels_rect[fill_black, :3] = 0.0
        pixels_rect[fill_white, :3] = 1.0

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__binarize_rect(
            img, rect, context.scene.pt_binarize_threshold,
            context.scene.pt_binarize_threshold_color)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_GrayScaleRect(bpy.types.Operator):

    bl_idname = "paint.pt_gray_scale_rect"
    bl_label = "Gray Scale Rect"
    bl_description = "Gray Scale Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __gray_scale_rect(self, img, rect, color):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels']

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + x + x0) * 4
                if color in ('RED', 'GREEN', 'BLUE'):
                    i = ['RED', 'GREEN', 'BLUE'].index(color)
                    c = pixels[offset + i]
                elif color == 'AVERAGE':
                    c = pixels[offset] + pixels[offset + 1] + pixels[offset + 2]
                    c = c / 3
                elif color == 'NTSC':
                    c = 0.298912 * pixels[offset]
                    c = c + 0.586611 * pixels[offset + 1]
                    c = c + 0.114478 * pixels[offset + 2]

                pixels[offset:offset+3] = c


    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__gray_scale_rect(img, rect, context.scene.pt_gray_scale_color)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_ChangeBrightnessRect(bpy.types.Operator):

    bl_idname = "paint.pt_change_brightness_rect"
    bl_label = "Change Brightness Rect"
    bl_description = "Change Brightness Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __change_brightness_rect(self, img, rect, brightness):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels']
        b = brightness / 255.0

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + x + x0) * 4
                pixels[offset] = pixels[offset] + b
                pixels[offset + 1] = pixels[offset + 1] + b
                pixels[offset + 2] = pixels[offset + 2] + b


    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__change_brightness_rect(
            img, rect, context.scene.pt_change_brightness_value)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_InvertRect(bpy.types.Operator):

    bl_idname = "paint.pt_invert_rect"
    bl_label = "Invert Rect"
    bl_description = "Invert Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __invert_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels']

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + x + x0) * 4
                pixels[offset] = 1.0 - pixels[offset]
                pixels[offset + 1] = 1.0 - pixels[offset + 1]
                pixels[offset + 2] = 1.0 - pixels[offset + 2]

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__invert_rect(img, rect)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_SepiaRect(bpy.types.Operator):

    bl_idname = "paint.pt_sepia_rect"
    bl_label = "Sepia Rect"
    bl_description = "Sepia Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __sepia_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels']

        r = 240.0 / 255.0
        g = 200.0 / 255.0
        b = 145.0 / 255.0

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + x + x0) * 4
                c = 0.298912 * pixels[offset]
                c = c + 0.586611 * pixels[offset + 1]
                c = c + 0.114478 * pixels[offset + 2]
                pixels[offset] = c * r 
                pixels[offset + 1] = c * g
                pixels[offset + 2] = c * b

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__sepia_rect(img, rect)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_CropRect(bpy.types.Operator):

    bl_idname = "paint.pt_crop_rect"
    bl_label = "Crop Rect"
    bl_description = "Crop Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __crop_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels']

        data = []
        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + x + x0) * 4
                data.extend(
                    [pixels[offset], pixels[offset + 1],
                    pixels[offset + 2], pixels[offset + 3]])

        img['image'].scale(x1 - x0, y1 - y0)
        img['image'].update()
        img['pixels'] = np.array(img['image'].pixels[:])
        pixels = img['pixels']

        n = 0
        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = (y * (x1 - x0) + x) * 4
                for i in range(4):
                    pixels[offset + i] = data[n + i]
                n = n + 4

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__crop_rect(img, rect)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_GammaCorrectRect(bpy.types.Operator):

    bl_idname = "paint.pt_gamma_correct_rect"
    bl_label = "Gamma Correct Rect"
    bl_description = "Gamma Correct Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __gamma_correct_rect(self, img, rect, gamma):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels']
        gamma_rec = 1.0 / gamma

        for y in range(y1 - y0):
            for x in range(x1 - x0):
                offset = ((y + y0) * w + x + x0) * 4
                pixels[offset] = pow(pixels[offset], gamma_rec)
                pixels[offset + 1] = pow(pixels[offset + 1], gamma_rec)
                pixels[offset + 2] = pow(pixels[offset + 2], gamma_rec)

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__gamma_correct_rect(img, rect, context.scene.pt_gamma)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_HorizontalFlipRect(bpy.types.Operator):

    bl_idname = "paint.pt_horizontal_flip_rect"
    bl_label = "Horizontal Flip Rect"
    bl_description = "Horizontal Flip Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __horizontal_flip_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels'].reshape((h, w, 4))
        pixels[y0:y1, x0:x1] = pixels[y0:y1, x1:x0:-1]

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__horizontal_flip_rect(img, rect)

        img['image'].pixels[:] = img['pixels'].tolist()
        img['image'].update()

        return {'FINISHED'}


class PT_VerticalFlipRect(bpy.types.Operator):

    bl_idname = "paint.pt_vertical_flip_rect"
    bl_label = "Vertical Flip Rect"
    bl_description = "Vertical Flip Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __vertical_flip_rect(self, img, rect):
        x0 = max(0, rect['x0'])
        y0 = max(0, rect['y0'])
        x1 = max(0, rect['x1'])
        y1 = max(0, rect['y1'])
        w = img['width']
        h = img['height']
        pixels = img['pixels'].reshape((h, w, 4))
        pixels[y0:y1, x0:x1] = pixels[y1:y0:-1, x0:x1]

    def execute(self, context):
        img = get_img_info(context)
        rect = get_pixel_rect_bb(context)
        self.__vertical_flip_rect(img, rect)

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
        mr = self.__get_mouse_position(context, event)
        if props.running is False:
            props.start = mr
            props.end = props.start
            PT_BoxRenderer.handle_remove(self, context)
            props.running = False
            return {'FINISHED'}
        
        region = context.region
        m = event.mouse_region_x, event.mouse_region_y
        is_inside = (0 <= m[0] < region.width) and (0 <= m[1] < region.height)

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if not props.selecting and is_inside:
                    props.selecting = True
                    props.start = mr
                    props.end = props.start
                    return {'RUNNING_MODAL'}
            elif event.value == 'RELEASE':
                if props.selecting:
                    props.selecting = False
                    props.end = mr
                    return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':
            if props.selecting:
                props.end = mr

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
    bl_region_type = 'TOOLS'
    bl_label = 'Painting Tools'
    bl_category = 'Paint Tools'

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='PLUGIN')

    def draw(self, context):
        sc = context.scene
        props = sc.pt_props
        layout = self.layout
        layout.label(text="Selection")
        if props.running == False:
            layout.operator(
                PT_BoxRenderer.bl_idname, text="Rectangular",
                icon='BORDER_RECT')
        else:
            layout.operator(PT_BoxRenderer.bl_idname, text="", icon='PAUSE')

            layout.separator()
            layout.separator()

            col = layout.column()
            col.operator(
                PT_SelectAll.bl_idname, text="Select All", icon='FULLSCREEN')

            layout.separator()

            col = layout.column()
            row = col.row()
            row.operator(PT_CopyRect.bl_idname, text="Copy")
            row.operator(PT_CutRect.bl_idname, text="Cut")
            row.operator(PT_PasteRect.bl_idname, text="Paste")
            row.operator(PT_CropRect.bl_idname, text="Crop")

            layout.separator()

            col = layout.column()
            col.operator(PT_FillRect.bl_idname, text="Fill", icon='TPAINT_HLT')
            row = col.row()
            row.label(text="Color:")
            row.prop(sc, "pt_fill_color", text="")

            layout.separator()

            col = layout.column()
            col.operator(PT_EraseRect.bl_idname, text="Erase", icon='X_VEC')

            layout.separator()

            col = layout.column()
            col.operator(
                PT_BinarizeRect.bl_idname, text="Binarize", icon='IMAGE_ALPHA')
            split = layout.split()
            col = split.column()
            col.label(text="Threshold:")
            col.prop(sc, "pt_binarize_threshold", text="")
            col = split.column()
            col.label(text="Color:")
            col.prop(sc, "pt_binarize_threshold_color", text="")

            layout.separator()

            col = layout.column()
            col.operator(
                PT_GrayScaleRect.bl_idname, text="Gray Scale",
                icon='IMAGE_ZDEPTH')
            row = col.row()
            row.label(text="Color:")
            row.prop(sc, "pt_gray_scale_color", text="")

            layout.separator()

            col = layout.column()
            col.operator(
                PT_ChangeBrightnessRect.bl_idname, text="Change Brightness",
                icon='LAMP_SUN')
            row = col.row()
            row.label(text="Brightness:")
            row.prop(sc, "pt_change_brightness_value", text="")

            layout.separator()

            col = layout.column()
            row = col.row()
            row.operator(
                PT_InvertRect.bl_idname, text="Invert", icon="SEQ_CHROMA_SCOPE")
            row.operator(
                PT_SepiaRect.bl_idname, text="Sepia")
            row = col.row()
            row.operator(
                PT_GammaCorrectRect.bl_idname, text="Gamma Correction")
            row = col.row()
            row.label(text="Gamma:")
            row.prop(sc, "pt_gamma", text="")

            layout.separator()

            col = layout.column()
            row = col.row()
            row.operator(PT_HorizontalFlipRect.bl_idname, text="Flip H")
            row.operator(PT_VerticalFlipRect.bl_idname, text="Flip V")


class PTProps():
    running = False
    selecting = False
    start = (0.0, 0.0)
    end = (0.0, 0.0)
    copied_pixels = None


def init_props():
    scene = bpy.types.Scene
    scene.pt_props = PTProps()
    scene.pt_fill_color = FloatVectorProperty(
        name="Fill Color",
        description="Filled by this color",
        subtype='COLOR_GAMMA',
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
    scene.pt_gray_scale_color = EnumProperty(
        name="Gray Scale Color",
        description="Gray Scale Color",
        items=[
            ('NTSC', "NTSC", "NTSC"),
            ('AVERAGE', "Average", "Average"),
            ('RED', "Red", "Red"),
            ('GREEN', "Green", "Green"),
            ('BLUE', "Blue", "Blue")],
        default='NTSC')
    scene.pt_change_brightness_value = IntProperty(
        name="Brightness",
        description="Brightness",
        default=0,
        min=-255,
        max=255)
    scene.pt_gamma = FloatProperty(
        name="Gamma",
        description="Gamma value used by gamma correction",
        default=1.0,
        min=1.0,
        max=10.0)
 

def clear_props():
    scene = bpy.types.Scene
    del scene.pt_fill_color
    del scene.pt_props
    del scene.pt_binarize_threshold
    del scene.pt_binarize_threshold_color
    del scene.pt_gray_scale_color
    del scene.pt_change_brightness_value
    del scene.pt_gamma


def register():
    bpy.utils.register_module(__name__)
    init_props()


def unregister():
    bpy.utils.unregister_module(__name__)
    clear_props()


if __name__ == "__main__":
    register()

