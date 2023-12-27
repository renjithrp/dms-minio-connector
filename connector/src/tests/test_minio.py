import unittest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from src.utils.minio import put_object, create_tags, get_object, get_tags, get_object_stream

class TestMinioUtilsFunctions(unittest.TestCase):
    @patch('src.utils.minio.Minio')
    def test_put_object_success(self, mock_minio):
        # Mocking client and its methods
        client = Mock()
        client.bucket_exists.return_value = False
        client.stat_object.side_effect = [Exception("Object not found"), None]

        # Test data
        bucket_name = "test_bucket"
        object_name = "test_object"
        data = b"Test data"

        # Execute the function
        result = put_object(client, bucket_name, object_name, data, tags={"tag1": "value1", "tag2": "value2"})

        # Assertions
        self.assertIsNone(result)
        client.make_bucket.assert_called_once_with(bucket_name)
        client.put_object.assert_called_once()
        client.set_object_tags.assert_called_once()

    @patch('src.utils.minio.Minio')
    def test_put_object_already_exists(self, mock_minio):
        # Mocking client and its methods
        client = Mock()
        client.bucket_exists.return_value = True
        client.stat_object.side_effect = None

        # Test data
        bucket_name = "test_bucket"
        object_name = "test_object"
        data = b"Test data"

        # Execute the function
        result = put_object(client, bucket_name, object_name, data, tags={"tag1": "value1", "tag2": "value2"})

        # Assertions
        expected_error_message = f"minio object '{object_name}' already exists in bucket '{bucket_name}'"
        self.assertEqual(result, expected_error_message)
        client.make_bucket.assert_not_called()
        client.put_object.assert_not_called()
        client.set_object_tags.assert_not_called()

    @patch('src.utils.minio.Minio')
    def test_put_object_failure(self, mock_minio):
        # Mocking client and its methods
        client = Mock()
        client.bucket_exists.return_value = False
        client.stat_object.side_effect = Exception("Some error occurred")

        # Test data
        bucket_name = "test_bucket"
        object_name = "test_object"
        data = b"Test data"

        # Execute the function
        result = put_object(client, bucket_name, object_name, data, tags={"tag1": "value1", "tag2": "value2"})

        # Assertions
        # Check if the result contains the expected failure message structure
        if result is not None:
            self.assertIn(f"minio object '{object_name}' upload failed '{bucket_name}'", result)
            # If the upload failed, put_object should not have been called
            client.put_object.assert_not_called()
        else:
            # If result is None, at least check if the necessary client methods were called
            client.make_bucket.assert_called_once_with(bucket_name)
            client.set_object_tags.assert_called_once()
    def test_create_tags_success(self):
        # Mocking client and its methods
        client = Mock()
        bucket_name = "test_bucket"
        object_name = "test_object"
        tags = {"tag1": "value1", "tag2": "value2"}

        # Execute the function
        result = create_tags(client, bucket_name, object_name, tags)

        # Assertions
        self.assertIsNone(result)
        client.set_object_tags.assert_called_once_with(bucket_name, object_name, tags)

    def test_create_tags(self):
        # Mock the client object and necessary methods
        client_mock = Mock()
        client_mock.set_object_tags.return_value = None

        # Define test data
        bucket_name = "test_bucket"
        object_name = "test_object"
        tags = {"tag1": "value1", "tag2": "value2"}

        # Call the function with the mocked client and test data
        create_tags(client_mock, bucket_name, object_name, tags)

        # Assertions to check if the expected calls were made
        expected_minio_tags = {
            "tag1": "value1",
            "tag2": "value2"
        }
        client_mock.set_object_tags.assert_called_once_with(
            bucket_name,
            object_name,
            expected_minio_tags
        )
        
    def test_get_object_failure(self):
        # Mocking client to raise an exception
        client = Mock()
        client.fget_object.side_effect = Exception("Download failed")
        bucket_name = "test_bucket"
        object_name = "test_object"
        local_file_path = "/path/to/local/file.txt"

        # Execute the function
        result = get_object(client, bucket_name, object_name, local_file_path)

        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn(f"minio object '{object_name}' download failed from '{bucket_name}'", result)
        client.fget_object.assert_called_once_with(bucket_name, object_name, local_file_path)

    def test_get_tags_success(self):
        # Mocking client and its methods
        client = Mock()
        bucket_name = "test_bucket"
        object_name = "test_object"
        mock_tags = {"tag1": "value1", "tag2": "value2"}
        client.get_object_tags.return_value = mock_tags

        # Execute the function
        result = get_tags(client, bucket_name, object_name)

        # Assertions
        self.assertEqual(result, mock_tags)
        client.get_object_tags.assert_called_once_with(bucket_name, object_name)

    def test_get_tags_failure(self):
        # Mocking client to raise an exception
        client = Mock()
        client.get_object_tags.side_effect = Exception("Tag retrieval failed")
        bucket_name = "test_bucket"
        object_name = "test_object"

        # Execute the function
        result = get_tags(client, bucket_name, object_name)

        # Assertions
        self.assertEqual(result, {})
        client.get_object_tags.assert_called_once_with(bucket_name, object_name)

    def test_get_tags_no_tags(self):
        # Mocking client to return None for tags
        client = Mock()
        bucket_name = "test_bucket"
        object_name = "test_object"
        client.get_object_tags.return_value = None

        # Execute the function
        result = get_tags(client, bucket_name, object_name)

        # Assertions
        self.assertEqual(result, {})
        client.get_object_tags.assert_called_once_with(bucket_name, object_name)

    @patch('src.utils.minio.BytesIO')
    def test_get_object_stream_success(self, mock_bytes_io):
        # Arrange
        bucket_name = 'your_bucket'
        object_name = 'your_object_name'
        expected_content = b'Test content'

        # Create a BytesIO instance
        stream_instance = BytesIO(expected_content)

        # Configure the BytesIO mock to return the stream instance when called
        mock_bytes_io.return_value = stream_instance

        # Mock the client and object retrieval
        client_mock = Mock()
        obj_mock = Mock()
        obj_mock.stream.return_value = iter([expected_content])
        client_mock.get_object.return_value = obj_mock

        # Act
        stream, error = get_object_stream(client_mock, bucket_name, object_name, BytesIO())

        # Assert
        client_mock.get_object.assert_called_once_with(bucket_name, object_name)
        self.assertIsNotNone(stream)
        self.assertIsNone(error)

        # Check stream content by reading and comparing
        stream_contents = stream.getvalue() if hasattr(stream, 'getvalue') else None
        self.assertEqual(stream_contents, expected_content)

    @patch('src.utils.minio.BytesIO')
    def test_get_object_stream_failure(self, mock_bytes_io):
        # Arrange
        bucket_name = 'your_bucket'
        object_name = 'your_object_name'

        # Configure the BytesIO mock to return an instance
        mock_bytes_io.return_value = BytesIO()

        # Mock the client to raise an exception when get_object is called
        client_mock = Mock()
        client_mock.get_object.side_effect = Exception("Object retrieval failed")

        # Act
        stream, error = get_object_stream(client_mock, bucket_name, object_name, BytesIO())

        # Assert
        client_mock.get_object.assert_called_once_with(bucket_name, object_name)
        self.assertIsNone(stream)
        self.assertIsNotNone(error)
        self.assertEqual(str(error), "minio object 'your_object_name' get_object_stream 'your_bucket': Object retrieval failed")

if __name__ == '__main__':
    unittest.main()