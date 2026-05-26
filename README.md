# 🎯 Smart Notes Application

A modern, full-stack notes application built with Flask that supports both **local** and **cloud** storage modes.

## ✨ Features

- 📝 **Create & Manage Notes** - Add, edit, delete, and organize notes
- 🏷️ **Smart Tagging** - Auto-generated tags using keyword-based AI
- 📁 **Subject Organization** - Group notes by subject/category
- ⭐ **Pin Important Notes** - Mark your most important notes
- 🔍 **Smart Search** - Find notes by title or content
- 📎 **File Attachments** - Support for PDF, DOCX, TXT, and image files
- 🌐 **Hybrid Architecture** - Works with both local SQLite and AWS DynamoDB
- 📊 **Statistics** - Track total and pinned notes
- 🎨 **Beautiful UI** - Modern, responsive design

## 🏗️ Architecture

### Local Mode (Default)
- **Database**: SQLite (local file)
- **Storage**: Local file system (`/local_storage`)
- **Tagging**: Keyword-based Python logic
- **Best for**: Development, offline usage, demos

### Cloud Mode
- **Database**: AWS DynamoDB
- **Storage**: Amazon S3
- **Tagging**: Mock AWS Comprehend API
- **Best for**: Production, multi-user, scalability

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git (optional)

### Installation

1. **Clone or Download the Project**
```bash
git clone <repository-url>
cd smart-notes-app
