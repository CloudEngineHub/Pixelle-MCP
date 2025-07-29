#!/bin/bash
set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Color output functions
print_info() {
    echo "🚀 $1"
}

print_success() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
}

print_warning() {
    echo "⚠️  $1"
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "Please install uv first"
        echo "Installation: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
}

# Stop existing services
stop_services() {
    if [ -f "$PID_FILE" ]; then
        print_info "Stopping existing services..."
        while read -r line; do
            if [ -n "$line" ]; then
                IFS=' ' read -ra PIDS <<< "$line"
                for pid in "${PIDS[@]}"; do
                    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                        print_info "Stopping process $pid"
                        kill -TERM "$pid" 2>/dev/null || true
                        # Wait for graceful exit
                        sleep 2
                        # Force kill if still running
                        if kill -0 "$pid" 2>/dev/null; then
                            print_warning "Force stopping process $pid"
                            kill -KILL "$pid" 2>/dev/null || true
                        fi
                    fi
                done
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        print_success "All services stopped"
    else
        print_info "No running services found"
    fi
}

# Check if port is occupied
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port is occupied, attempting to release..."
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t)
        if [ -n "$pid" ]; then
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
    fi
}

# Start single service
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    local daemon_mode=$4
    
    print_info "Starting $service_name..."
    cd "$SCRIPT_DIR/$service_dir"
    
    # Sync dependencies
    uv sync
    
    # Check and release port
    check_port "$port"
    
    if [ "$daemon_mode" = "true" ]; then
        # Background mode, output to log file
        nohup uv run main.py > "$LOG_DIR/$service_name.log" 2>&1 &
        local pid=$!
        echo $pid >> "$PID_FILE"
        print_success "$service_name started in background (PID: $pid, Log: $LOG_DIR/$service_name.log)"
    else
        # Foreground mode
        uv run main.py &
        local pid=$!
        echo $pid >> "$PID_FILE"
        print_success "$service_name started (PID: $pid)"
    fi
    
    cd "$SCRIPT_DIR"
    
    # Wait for service to start
    sleep 3
    if ! kill -0 "$pid" 2>/dev/null; then
        print_error "$service_name failed to start"
        return 1
    fi
}

# Start all services
start_services() {
    local daemon_mode=$1
    
    print_info "Starting Pixelle MCP services..."
    
    # Clear PID file
    > "$PID_FILE"
    
    # Start base service
    start_service "mcp-base" "mcp-base" "9001" "$daemon_mode"
    
    # Start server service  
    start_service "mcp-server" "mcp-server" "9002" "$daemon_mode"
    
    # Start client service
    start_service "mcp-client" "mcp-client" "9003" "$daemon_mode"
    
    print_success "All services started successfully!"
    echo "🌐 Client: http://localhost:9003"
    echo "🗄️ Server: http://localhost:9002/sse"  
    echo "🔧 Base Service: http://localhost:9001/docs"
    
    if [ "$daemon_mode" = "true" ]; then
        echo "📋 Log directory: $LOG_DIR"
        echo "🔍 Check status: $0 status"
        echo "🛑 Stop services: $0 stop"
    fi
}

# Check service status
show_status() {
    print_info "Checking service status..."
    
    if [ ! -f "$PID_FILE" ]; then
        print_info "No running services"
        return
    fi
    
    local running_count=0
    local services=("mcp-base:9001" "mcp-server:9002" "mcp-client:9003")
    local line_num=0
    
    while read -r pid; do
        if [ -n "$pid" ] && [ "$line_num" -lt 3 ]; then
            local service_info="${services[$line_num]}"
            local service_name="${service_info%%:*}"
            local port="${service_info##*:}"
            
            if kill -0 "$pid" 2>/dev/null; then
                print_success "$service_name is running (PID: $pid, Port: $port)"
                running_count=$((running_count + 1))
            else
                print_error "$service_name is not running"
            fi
            line_num=$((line_num + 1))
        fi
    done < "$PID_FILE"
    
    echo "Running services: $running_count/3"
}

# Show help information
show_help() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start            Start all services (foreground)"
    echo "  start --daemon   Start all services (background)"
    echo "  stop             Stop all services"
    echo "  restart          Restart all services"
    echo "  status           Check service status"
    echo "  logs [service]   View service logs"
    echo "  help             Show help information"
    echo ""
    echo "Examples:"
    echo "  $0 start --daemon   # Start services in background"
    echo "  $0 logs mcp-client  # View client logs"
    echo "  $0 restart          # Restart all services"
}

# View logs
show_logs() {
    local service=$1
    
    if [ -z "$service" ]; then
        print_info "Available service logs:"
        ls -la "$LOG_DIR"/*.log 2>/dev/null || print_info "No log files found"
        return
    fi
    
    local log_file="$LOG_DIR/$service.log"
    if [ -f "$log_file" ]; then
        print_info "Showing $service logs (Ctrl+C to exit):"
        tail -f "$log_file"
    else
        print_error "Log file not found for $service: $log_file"
    fi
}

# Main logic
main() {
    local command=""
    local daemon_mode=false
    local remaining_args=()
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --daemon|-d)
                daemon_mode=true
                shift
                ;;
            start|stop|restart|status|logs|help|--help|-h)
                command="$1"
                shift
                # Collect remaining arguments
                while [[ $# -gt 0 ]]; do
                    if [[ "$1" != "--daemon" && "$1" != "-d" ]]; then
                        remaining_args+=("$1")
                    else
                        daemon_mode=true
                    fi
                    shift
                done
                break
                ;;
            *)
                if [ -z "$command" ]; then
                    command="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Default to start if no command specified
    if [ -z "$command" ]; then
        command="start"
    fi
    
    case "$command" in
        start)
            check_uv
            stop_services
            if [ "$daemon_mode" = "true" ]; then
                start_services true
            else
                start_services false
                # Wait for any service to exit in foreground mode
                print_info "Press Ctrl+C to stop all services"
                trap 'stop_services; exit 0' INT TERM
                wait
            fi
            ;;
        stop)
            stop_services
            ;;
        restart)
            check_uv
            stop_services
            start_services true
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${remaining_args[0]}"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"