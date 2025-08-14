if __name__ == '__main__':
    # Start cleanup task
    from threading import Thread
    cleanup_thread = Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    
    # Get port from environment variables, adapt to cloud platform requirements
    port = int(os.getenv('PORT', 10000))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Log startup information
    logger.info(f"🚀 Grok 3.0 Chat Application Starting...")
    logger.info(f"📡 Server: {host}:{port}")
    logger.info(f"🔗 API URL: {API_URL}")
    logger.info(f"🤖 Model: {os.getenv('MODEL_NAME', 'grok-3-fast-latest')}")
    logger.info(f"🔧 Debug Mode: {debug_mode}")
    logger.info(f"💾 Max Conversations: {session_manager.max_conversations}")
    logger.info(f"💬 Max Messages per Conversation: {session_manager.max_messages_per_conversation}")
    logger.info(f"🔍 Live Search: Integrated with xAI API")
    
    try:
        # In cloud environments, host and port are usually automatically assigned
        socketio.run(
            app, 
            host=host, 
            port=port,
            debug=debug_mode,
            use_reloader=False,  # Disable reloader for production
            log_output=debug_mode  # Only log output in debug mode
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1) 