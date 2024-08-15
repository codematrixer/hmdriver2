import unittest
from hmdriver2 import add, subtract, logger


class TestCoreFunctions(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

    def test_subtract(self):
        self.assertEqual(subtract(2, 1), 1)

    def test_logger(self):
        logger.enabled = True
        logger.info("This is an info message")
        logger.error("This is an error message")

        logger.enabled = False
        logger.info("This message should not appear")


if __name__ == "__main__":
    unittest.main()