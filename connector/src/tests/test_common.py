import unittest
from unittest.mock import patch, MagicMock
from src.utils.common import get_unique_19_digit_id

class TestFunctions(unittest.TestCase):
    
    @patch('src.utils.common.initialize_redis_client')
    def test_get_unique_19_digit_id(self, mock_redis_conn):
        # Mock the Redis client and its methods
        redis_client = MagicMock()
        mock_redis_conn.return_value = redis_client
        redis_client.set.return_value = True
        redis_client.get.return_value = b'100'  # Simulate an existing stored ID
        
        # Run the function
        result = get_unique_19_digit_id()
        
        # Assertions
        self.assertEqual(
             len(str(result)),
             19,
            f"Expected {result} to be equal to 1703301373627668300. Redis client calls: {redis_client.method_calls}"
        )

if __name__ == '__main__':
    unittest.main()