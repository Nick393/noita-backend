import os

from PIL import Image

MAP_X_RANGE, MAP_Y_RANGE = [-4096, 4096], [-2048, 14336]

def image_from_game_id(game_id: str) -> Image.Image:
    # the size of the standard section of the world (just main 7 areas) is roughly [-4096,4096] X * [-2048,14336] Y
    if os.path.isfile(f"{game_id}.png"): # TODO: check if image is in database
        # this should still return an Image - how exactly you do that is up to you
        return Image.open(f"{game_id}.png") # TODO: load image from database and return as a PIL image
    else:
        return init_new_image()


# initializes a new image from the template we've manually generated
def init_new_image() -> Image.Image:
    if not os.path.isfile('map_template.png'):
        raise Exception("Map template not found. Please manually generate one using the img_utils.manual_generate_template_image() function.")

    image_template = Image.open('map_template.png')
    image = image_template.copy()
    image.putalpha(0)
    return image


def add_terrain_to_image(image: Image.Image, bounds: dict, terrain_data: list[list[int]]):
    image_pixels = image.load()
    if not image_pixels:
        raise Exception("failed to add pixels to image")

    # iterate through our 2D nested list of world pixels, updating corresponding pixels in the image
    for y, row in enumerate(terrain_data, start=bounds['min_y']):
        for x, pixel in enumerate(row, start=bounds['min_x']):
            # don't update pixels out of the bounds of our image
            if not (MAP_X_RANGE[0] <= x < MAP_X_RANGE[1]) or not (MAP_Y_RANGE[0] <= y < MAP_Y_RANGE[1]):
                continue

            # convert game-world coordinates (origin is in the middle of the world) to image coordinates (origin in top left corner of the image) 
            img_y = (y - MAP_Y_RANGE[0])
            img_x = (x - MAP_X_RANGE[0])

            # update the pixel's alpha channel to 0 (transparent) for pixels that aren't in the world, and to 255 (opaque) for pixels that are 
            image_pixels[img_x, img_y] = image_pixels[img_x,img_y][:3]+(255*pixel,)



# maps pixel colors in the biome_map to what texture those biome locations should have in our map; this is used when generating our template
# the choices here are somewhat arbitrary; I just picked textures of common materials within each biome
def biome_map_color_to_ingame_image_pixels(biome_map_color):
    IMG_FOLDER = "material_textures"

    # helper function to load a Pillow image texture from a file name
    def get_image_texture(texture_file_name):
        with Image.open(os.path.join(IMG_FOLDER, texture_file_name)) as image:
            size = image.size
            texture = image.load()
            return size, texture

    # holy mountains have a bunch of different biome colors
    # they almost all share the same R & G values and are slightly different in B
    # we'll texture them all as temple brick
    HOLY_MOUNTAIN_COLORS = [(109, 203, 40), (90, 150, 40)] + [(147, 203, blue) for blue in (76, 77, 78, 90)]
    match biome_map_color:
        case biome_map_color if biome_map_color in HOLY_MOUNTAIN_COLORS:
            return get_image_texture("templebrick.png")

        case (213, 121, 23) | (213, 101, 23): # mines and collapsed mines
            return get_image_texture("earth.png")

        case (18, 68, 69): # coal pits
            return get_image_texture("coal_static.png")

        case (232, 97, 240): # fungal caverns
            return get_image_texture("fungi.png")

        case (23, 117, 213): # snowy depths
            return get_image_texture("snowrock_bright.png")

        case (0, 70, 255): # hiisi base
            return get_image_texture("steelpanel.png")
        
        case (128, 128, 0) | (160, 132, 0): # jungle technically has two different biome colors
            return get_image_texture("earth_rainforest.png")
        
        case (0, 128, 0): # vault
            return get_image_texture("vaultrock.png")

        case (120, 108, 66): # temple of the art
            return get_image_texture("templebrick_alt.png")

        case (61, 61, 61): # usually filled with (extremely) dense rock
            return get_image_texture("rock_hard_border.png")

        case (255, 167, 23) | (255, 106, 2): # lava lakes below final holy mountain
            # since lava is a solid color ingame, there's no need to load a texture file for it; we just make a 1-pixel Image of that color
            return (1, 1), Image.new('RGB', (1,1), (255, 129, 0)).load() # type: ignore

        case _: # default to regular stone (normally found around the entrance to the mines)
            return get_image_texture("rock.png")


# used to generate an image that will unveil as you explore the world
# this is meant to be run once (by hand), and the resulting image is saved and then copied each time a run is started
# we start with it opaque so we can see that it worked properly, but when we initialize this for each player, we'll set all pixels to transparent
# this generates a template, so we'll copy it for each player who starts a run
def manual_generate_template_image(): 
    NOITA_MAP_SIZE = (MAP_X_RANGE[1] - MAP_X_RANGE[0], MAP_Y_RANGE[1] - MAP_Y_RANGE[0])
    # create a blank image that's the size of our defined noita world
    template_image = Image.new(mode='RGBA', size=NOITA_MAP_SIZE)
    template_image_pixels = template_image.load()
    
    # the biome map defines what kind of terrain the game generates in each 512x512-pixel 'chunk' of the world
    # I've trimmed it to only include the part of the world we're mapping
    # right now, this is a manual process that only needed to be done once
    with Image.open("biome_map_trimmed.png") as BIOME_MAP: 
        biome_map_width, biome_map_height = BIOME_MAP.size
        BIOME_MAP_PIXELS = BIOME_MAP.load()

    # we loop over each pixel in the biome map (equivalent to a 512x512-pixel chunk ingame)
    for biome_map_x in range(biome_map_width):
        for biome_map_y in range(biome_map_height):
            print("writing map chunk", biome_map_x, biome_map_y)
            biome_map_color = BIOME_MAP_PIXELS[biome_map_x, biome_map_y]

            # each pixel color in the biome map is associated with a texture tiled over that chunk in the map we're generating
            # we load that texture (and its size, for ease-of-access) here
            texture_size, texture_pixels = biome_map_color_to_ingame_image_pixels(biome_map_color)
            # and then loop over the associated chunk in the template image we're generating
            for img_x in range(biome_map_x*512, biome_map_x*512+512):
                for img_y in range(biome_map_y*512, biome_map_y*512+512):
                    # this modulo lets us tile the texture over the entire chunk
                    texture_x = img_x % texture_size[0]
                    texture_y = img_y % texture_size[1]
                    pixel_color = texture_pixels[texture_x, texture_y]
                    if len(pixel_color) == 3: # add an opaque alpha channel if it doesn't exist
                        pixel_color += (255,)

                    template_image_pixels[img_x, img_y] = pixel_color

    print("saving template...", end="")
    template_image.save("map_template.png")
    print("saved")
    return template_image

