"""File upload handler."""
import os


class FileUploadHandler:
    """Handle uploaded files."""

    def __init__(self, uploadDirectory):
        self.uploadDirectory = uploadDirectory

    def saveFile(self, fileName, fileContent):
        """Save uploaded file to disk."""
        filePath = os.path.join(self.uploadDirectory, fileName)
        with open(filePath, 'wb') as f:
            f.write(fileContent)

    def getFileSize(self, fileName):
        """Get size of uploaded file."""
        filePath = os.path.join(self.uploadDirectory, fileName)
        return os.path.getsize(filePath)
