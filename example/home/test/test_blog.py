import datetime
import decimal

import wagtail_factories
from django.conf import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.safestring import SafeText
from wagtail.core.blocks import BoundBlock, StreamValue, StructValue
from wagtail.core.rich_text import RichText
from wagtail.embeds.blocks import EmbedValue

from example.tests.test_grapple import BaseGrappleTest
from home.blocks import (
    ButtonBlock,
    ImageGalleryImage,
    ImageGalleryImages,
    VideoBlock,
    CarouselBlock,
)
from home.factories import (
    BlogPageFactory,
    BlogPageRelatedLinkFactory,
    ImageGalleryImageFactory,
    AuthorPageFactory,
)


class BlogTest(BaseGrappleTest):
    def setUp(self):
        super().setUp()
        # Create Blog
        self.blog_page = BlogPageFactory(
            body=[
                ("heading", "Test heading 1"),
                ("paragraph", RichText("This is a paragraph.")),
                ("heading", "Test heading 2"),
                ("image", wagtail_factories.ImageFactory()),
                ("decimal", decimal.Decimal(1.2)),
                ("date", datetime.date.today()),
                ("datetime", datetime.datetime.now()),
                (
                    "carousel",
                    StreamValue(
                        stream_block=CarouselBlock(),
                        stream_data=[
                            ("image", wagtail_factories.ImageChooserBlockFactory()),
                            ("image", wagtail_factories.ImageChooserBlockFactory()),
                        ],
                    ),
                ),
                (
                    "gallery",
                    {
                        "title": "Gallery title",
                        "images": StreamValue(
                            stream_block=ImageGalleryImages(),
                            stream_data=[
                                (
                                    "image",
                                    {
                                        "image": wagtail_factories.ImageChooserBlockFactory()
                                    },
                                ),
                                (
                                    "image",
                                    {
                                        "image": wagtail_factories.ImageChooserBlockFactory()
                                    },
                                ),
                            ],
                        ),
                    },
                ),
                ("callout", {"text": RichText("<p>Hello, World</p>")}),
                ("objectives", ["Read all of article!"]),
                ("video", {"youtube_link": EmbedValue("https://youtube.com/")}),
                (
                    "text_and_buttons",
                    {
                        "text": "Button text",
                        "buttons": [
                            {
                                "button_text": "btn",
                                "button_link": "https://www.graphql.com/",
                            }
                        ],
                    },
                ),
            ]
        )

    def test_blog_page(self):
        query = """
        {
            page(id:%s) {
                ... on BlogPage {
                    title
                }
            }
        }
        """ % (
            self.blog_page.id
        )
        executed = self.client.execute(query)

        # Check title.
        self.assertEquals(executed["data"]["page"]["title"], self.blog_page.title)

    def test_related_author_page(self):
        query = """
        {
            page(id:%s) {
                ... on BlogPage {
                    author {
                        ... on AuthorPage {
                            name
                        }
                    }
                }
            }
        }
        """ % (
            self.blog_page.id
        )
        executed = self.client.execute(query)
        page = executed["data"]["page"]["author"]
        self.assertTrue(
            isinstance(page["name"], str) and page["name"] == self.blog_page.author.name
        )

    def get_blocks_from_body(self, block_type, block_query="rawValue"):
        query = """
        {
            page(id:%s) {
                ... on BlogPage {
                    body {
                        blockType
                        ... on %s {
                            %s
                        }
                    }
                }
            }
        }
        """ % (
            self.blog_page.id,
            block_type,
            block_query,
        )
        executed = self.client.execute(query)

        # Print the error response
        if not executed.get("data"):
            print(executed)

        blocks = []
        for block in executed["data"]["page"]["body"]:
            if block["blockType"] == block_type:
                blocks.append(block)
        return blocks

    def test_blog_body_charblock(self):
        block_type = "CharBlock"
        query_blocks = self.get_blocks_from_body(block_type)

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(query_blocks[count]["rawValue"], block.value)
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_richtextblock(self):
        block_type = "RichTextBlock"
        query_blocks = self.get_blocks_from_body(block_type)

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(
                    query_blocks[count]["rawValue"], block.value.__html__()
                )
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_imagechooserblock(self):
        block_type = "ImageChooserBlock"
        query_blocks = self.get_blocks_from_body(
            block_type,
            block_query="""
            image {
                id
                src
            }
            """,
        )

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(
                    query_blocks[count]["image"]["id"], str(block.value.id)
                )
                self.assertEquals(
                    query_blocks[count]["image"]["src"],
                    settings.BASE_URL + block.value.file.url,
                )
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_imagechooserblock(self):
        # Query stream block
        block_type = "CarouselBlock"
        query_blocks = self.get_blocks_from_body(
            block_type,
            block_query="""
                blocks {
                    ...on ImageChooserBlock {
                        image {
                            src
                        }
                    }
                }
            """,
        )

        # Get first image url
        url = query_blocks[0]["blocks"][0]["image"]["src"]

        # Check that src is valid url
        validator = URLValidator()
        try:
            # Run validator, If no exception thrown then we pass test
            validator(url)
        except ValidationError:
            self.fail(f"{url} is not a valid url")

    def test_blog_body_calloutblock(self):
        # Query stream block
        block_type = "CalloutBlock"
        query_blocks = self.get_blocks_from_body(
            block_type,
            block_query="""
                text
            """,
        )

        # Check HTML is string
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                html = query_blocks[0]["text"]
                self.assertEquals(type(html), SafeText)

    def test_blog_body_decimalblock(self):
        block_type = "DecimalBlock"
        query_blocks = self.get_blocks_from_body(block_type)

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(query_blocks[count]["rawValue"], str(block.value))
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_dateblock(self):
        block_type = "DateBlock"
        query_blocks = self.get_blocks_from_body(block_type)

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(query_blocks[count]["rawValue"], str(block.value))
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_datetimeblock(self):
        block_type = "DateTimeBlock"
        date_format_string = "%Y-%m-%d %H:%M:%S"
        query_blocks = self.get_blocks_from_body(
            block_type, block_query=f'value(format: "{date_format_string}")'
        )

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(
                    query_blocks[count]["value"],
                    block.value.strftime(date_format_string),
                )
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_imagegalleryblock(self):
        block_type = "ImageGalleryBlock"
        query_blocks = self.get_blocks_from_body(
            block_type,
            block_query="""
            title
            images {
                image {
                  id
                  src
                }
            }
            """,
        )

        # Check output.
        count = 0
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                # Test the values
                self.assertEquals(
                    query_blocks[count]["title"], str(block.value["title"])
                )
                for key, image in enumerate(query_blocks[count]["images"]):
                    self.assertEquals(
                        image["image"]["id"],
                        str(block.value["images"][key].value["image"].id),
                    )
                    self.assertEquals(
                        image["image"]["src"],
                        settings.BASE_URL
                        + str(block.value["images"][key].value["image"].file.url),
                    )
                # Increment the count
                count += 1
        # Check that we test all blocks that were returned.
        self.assertEquals(len(query_blocks), count)

    def test_blog_body_objectives(self):
        block_type = "ListBlock"
        query_blocks = self.get_blocks_from_body(
            block_type,
            block_query="""
            field
            items {
                ...on CharBlock {
                    value
                }
            }
            """,
        )
        # Check we have exactly one value
        self.assertEquals(len(query_blocks), 1)
        # Check that first value matches hardcoded value
        first_block = query_blocks[0]
        first_item = first_block.get("items", [])[0]
        first_value = first_item.get("value")
        self.assertEquals(first_value, "Read all of article!")

    def test_blog_embed(self):
        query = """
        {
            page(id:%s) {
                ... on BlogPage {
                    body {
                        blockType
                        ...on VideoBlock {
                            youtubeLink {
                                url
                            }
                        }
                    }
                }
            }
        }
        """ % (
            self.blog_page.id
        )
        executed = self.client.execute(query)
        body = executed["data"]["page"]["body"]

        for block in body:
            if block["blockType"] == "VideoBlock":
                self.assertTrue(isinstance(block["youtubeLink"]["url"], str))
                return

        self.fail("VideoBlock type not instantiated in Streamfield")

    # Next 2 tests are used to test the Collection API, both ForeignKey and nested field extraction.
    def test_blog_page_related_links(self):
        query = """
        {
            page(id:%s) {
                ... on BlogPage {
                    relatedLinks {
                        url
                    }
                }
            }
        }
        """ % (
            self.blog_page.id
        )
        executed = self.client.execute(query)

        links = executed["data"]["page"]["relatedLinks"]
        self.assertEqual(len(links), 5)
        for link in links:
            url = link.get("url", None)
            self.assertTrue(isinstance(url, str))

    def test_blog_page_related_urls(self):
        query = """
        {
            page(id:%s) {
                ... on BlogPage {
                    relatedUrls
                }
            }
        }
        """ % (
            self.blog_page.id
        )
        executed = self.client.execute(query)

        links = executed["data"]["page"]["relatedUrls"]
        self.assertEqual(len(links), 5)
        for url in links:
            self.assertTrue(isinstance(url, str))

    def test_structvalue_block(self):
        # Query stream block
        block_type = "TextAndButtonsBlock"
        query_blocks = self.get_blocks_from_body(
            block_type,
            block_query="""
                buttons {
                    ... on ButtonBlock {
                        buttonText
                        buttonLink
                    }
               }
            """,
        )

        # Check HTML is string
        for block in self.blog_page.body:
            if type(block.block).__name__ == block_type:
                buttons = query_blocks[0]["buttons"]
                self.assertEquals(buttons[0]["buttonText"], "btn")
                self.assertEquals(buttons[0]["buttonLink"], "https://www.graphql.com/")
