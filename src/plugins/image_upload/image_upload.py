from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageOps, ImageColor
from io import BytesIO
import logging
import random
import json
import re
from pathlib import Path
from utils.image_utils import resize_image

logger = logging.getLogger(__name__)


class ImageUpload(BasePlugin):

    def __get_cache_location(self, full_path):
        path = Path(full_path)
        base = path.parent.parent  # This is /usr/local/inkypi/src/static/images
        # Create the new path by joining the base + cached folder + filename
        cache_path = base / "cached" / path.name
        return str(cache_path)

    def __safeId(self, value):
        return '' if value == None else re.sub(r'[^a-zA-Z0-9_\-]', '_', re.sub(r'^.*[\\/]', '', value))

    def open_image(self, img_index: int, image_locations: list) -> Image:
        if not image_locations:
            raise RuntimeError("No images provided.")
        # Open the image using Pillow
        try:
            # First try to open the image from cache
            image = Image.open(self.__get_cache_location(image_locations[img_index]))
            logger.info('Using cached version of image.')
            using_cache = True
        except Exception as _:
            # No cached processed image found, open raw image instead
            try:
                image = Image.open(image_locations[img_index])
                using_cache = False
            except Exception as e:    
                logger.error(f"Failed to read image file: {str(e)}")
                raise RuntimeError("Failed to read image file.")
        return image, using_cache
        

    def generate_image(self, settings, device_config) -> Image:
        
        # Get the current index from the device json
        img_index = settings.get("image_index", 0)
        image_locations = settings.get("imageFiles[]")

        if img_index >= len(image_locations):
            # Prevent Index out of range issues when file list has changed
            img_index = 0

        if settings.get('randomize') == "true":
            img_index = random.randrange(0, len(image_locations))
            current_index = img_index
            image, using_cache = self.open_image(img_index, image_locations)
        else:
            image, using_cache = self.open_image(img_index, image_locations)
            current_index = img_index
            img_index = (img_index + 1) % len(image_locations)

        if using_cache:
            return image

        file_id = self.__safeId(image_locations[current_index])

        # Write the new index back ot the device json
        settings['image_index'] = img_index

        background_color = ImageColor.getcolor(settings.get('backgroundColor') or (255, 255, 255), "RGB")

        crop_settings = settings.get(f'crop_settings[{file_id}]')
        crop_params = json.loads(crop_settings or '{}')
        if len(crop_params) > 0:
            rotate = crop_params['rotate']
            if rotate != 0:
                image = image.rotate(-rotate, expand=True)

            temp = Image.new('RGB', (crop_params['width'], crop_params['height']), background_color)
            temp.paste(image, (-crop_params['x'], -crop_params['y']))
            image = temp

        ###
        if settings.get('padImage') == "true":
            dimensions = device_config.get_resolution()
            if device_config.get_config("orientation") == "vertical":
                dimensions = dimensions[::-1]
            frame_ratio = dimensions[0] / dimensions[1]
            img_width, img_height = image.size
            padded_img_size = (int(img_height * frame_ratio) if img_width >= img_height else img_width,
                              img_height if img_width >= img_height else int(img_width / frame_ratio))
            return ImageOps.pad(image, padded_img_size, color=background_color, method=Image.Resampling.LANCZOS)

        image = resize_image(image, device_config.get_resolution(), [])

        # Save to cache
        image.save(self.__get_cache_location(image_locations[current_index]))

        return image
