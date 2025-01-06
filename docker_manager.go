package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "strings"
    "time"
    "path/filepath"
    "os/exec"

    "github.com/docker/docker/api/types"
    "github.com/docker/docker/client"
    "github.com/gin-gonic/gin"
    "encoding/json"
    "encoding/base64"
    "io"
)

type ImageInfo struct {
    ID        string   `json:"id"`
    ShortID   string   `json:"short_id"`
    Name      string   `json:"name"`
    Tags      []string `json:"tags"`
    Size      string   `json:"size"`
    Created   string   `json:"created"`
    IsUsed    bool     `json:"is_used"`
}

// 添加删除进度响应结构
type DeleteProgress struct {
    Status      string   `json:"status"`
    Deleted     []string `json:"deleted"`
    Errors      []string `json:"errors"`
    TotalCount  int      `json:"total_count"`
    DeletedSize int64    `json:"deleted_size"`  // 已删除的大小（字节）
    TotalSize   int64    `json:"total_size"`    // 总大小（字节）
}

// 添加推送配置结构
type PushConfig struct {
    ImageIDs    []string `json:"image_ids"`
    Username    string   `json:"username"`
    Password    string   `json:"password"`
    ProxyType   string   `json:"proxy_type"`    // "http" 或 "socks5"
    ProxyServer string   `json:"proxy_server"`  // 代理服务器地址
}

// 添加自定义的推送进度结构体
type PushProgress struct {
    Status         string `json:"status"`
    Error          string `json:"error,omitempty"`
    Progress       string `json:"progress,omitempty"`
    ProgressDetail struct {
        Current int64 `json:"current"`
        Total   int64 `json:"total"`
    } `json:"progressDetail,omitempty"`
}

// 修改代理设置函数
func setProxy(proxyType, proxyServer string) {
    if proxyType != "" && proxyServer != "" {
        // 设置 Docker 客户端环境变量
        upperProxy := fmt.Sprintf("%s_PROXY", strings.ToUpper(proxyType))
        lowerProxy := fmt.Sprintf("%s_proxy", proxyType)
        
        os.Setenv(upperProxy, proxyServer)
        os.Setenv(lowerProxy, proxyServer)
        
        // 同时设置 HTTPS 代理
        os.Setenv("HTTPS_PROXY", proxyServer)
        os.Setenv("https_proxy", proxyServer)
        
        // 设置 Docker 守护进程的代理
        configPath := "/etc/systemd/system/docker.service.d/http-proxy.conf"
        proxyConfig := fmt.Sprintf(`[Service]
Environment="HTTP_PROXY=%s"
Environment="HTTPS_PROXY=%s"
Environment="NO_PROXY=localhost,127.0.0.1"`, proxyServer, proxyServer)

        // 确保目录存在
        os.MkdirAll("/etc/systemd/system/docker.service.d", 0755)
        
        // 写入配置文件
        if err := os.WriteFile(configPath, []byte(proxyConfig), 0644); err != nil {
            ErrorLogger.Printf("Failed to write proxy config: %v", err)
        }

        // 重启 Docker 守护进程
        exec.Command("systemctl", "daemon-reload").Run()
        exec.Command("systemctl", "restart", "docker").Run()
        
        // 等待 Docker 守护进程重启
        time.Sleep(5 * time.Second)
    }
}

// 修改清除代理函数
func clearProxy() {
    // 清除环境变量
    proxyTypes := []string{"http", "https", "socks5"}
    for _, pt := range proxyTypes {
        os.Unsetenv(fmt.Sprintf("%s_PROXY", strings.ToUpper(pt)))
        os.Unsetenv(fmt.Sprintf("%s_proxy", pt))
    }
    os.Unsetenv("NO_PROXY")
    os.Unsetenv("no_proxy")

    // 删除 Docker 守护进程代理配置
    os.Remove("/etc/systemd/system/docker.service.d/http-proxy.conf")
    
    // 重启 Docker 守护进程
    exec.Command("systemctl", "daemon-reload").Run()
    exec.Command("systemctl", "restart", "docker").Run()
    
    // 等待 Docker 守护进程重启
    time.Sleep(5 * time.Second)
}

// 添加日志记录器
var (
    InfoLogger  *log.Logger
    ErrorLogger *log.Logger
)

// 初始化日志
func init() {
    // 创建日志目录
    logDir := "logs"
    if err := os.MkdirAll(logDir, 0755); err != nil {
        log.Fatal("Failed to create log directory:", err)
    }

    // 创建或打开日志文件
    currentTime := time.Now().Format("2006-01-02")
    logFile, err := os.OpenFile(
        filepath.Join(logDir, fmt.Sprintf("docker-manager-%s.log", currentTime)),
        os.O_APPEND|os.O_CREATE|os.O_WRONLY,
        0644,
    )
    if err != nil {
        log.Fatal("Failed to open log file:", err)
    }

    // 设置日志格式
    InfoLogger = log.New(logFile, "INFO: ", log.Ldate|log.Ltime|log.Lshortfile)
    ErrorLogger = log.New(logFile, "ERROR: ", log.Ldate|log.Ltime|log.Lshortfile)
}

// 添加详细的错误日志结构
type DetailedError struct {
    Operation   string `json:"operation"`
    ImageID     string `json:"image_id"`
    ErrorCode   string `json:"error_code"`
    Message     string `json:"message"`
    Timestamp   string `json:"timestamp"`
}

func logError(operation string, imageID string, err error) DetailedError {
    // 解析错误代码
    errorCode := "UNKNOWN"
    if strings.Contains(err.Error(), "not found") {
        errorCode = "IMAGE_NOT_FOUND"
    } else if strings.Contains(err.Error(), "unauthorized") {
        errorCode = "UNAUTHORIZED"
    } else if strings.Contains(err.Error(), "connection refused") {
        errorCode = "CONNECTION_REFUSED"
    } else if strings.Contains(err.Error(), "timeout") {
        errorCode = "TIMEOUT"
    }

    detailedErr := DetailedError{
        Operation:   operation,
        ImageID:     imageID,
        ErrorCode:   errorCode,
        Message:     err.Error(),
        Timestamp:   time.Now().Format("2006-01-02 15:04:05"),
    }

    // 记录错误日志
    ErrorLogger.Printf("Operation: %s, ImageID: %s, ErrorCode: %s, Message: %s",
        detailedErr.Operation,
        detailedErr.ImageID,
        detailedErr.ErrorCode,
        detailedErr.Message,
    )

    return detailedErr
}

func main() {
    r := gin.Default()

    // 允许跨域
    r.Use(func(c *gin.Context) {
        c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
        c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type")
        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }
        c.Next()
    })

    // 获取镜像列表
    r.GET("/images", func(c *gin.Context) {
        InfoLogger.Println("Fetching image list")
        cli, err := client.NewClientWithOpts(client.FromEnv)
        if err != nil {
            detailedErr := logError("CREATE_CLIENT", "", err)
            c.JSON(500, gin.H{"error": detailedErr})
            return
        }
        defer cli.Close()

        // 获取所有镜像
        images, err := cli.ImageList(context.Background(), types.ImageListOptions{All: true})
        if err != nil {
            c.JSON(500, gin.H{"error": err.Error()})
            return
        }

        // 获取所有容器使用的镜像ID
        containers, err := cli.ContainerList(context.Background(), types.ContainerListOptions{All: true})
        if err != nil {
            c.JSON(500, gin.H{"error": err.Error()})
            return
        }

        usedImageIDs := make(map[string]bool)
        for _, container := range containers {
            usedImageIDs[container.ImageID] = true
        }

        // 构建响应数据
        var imageList []ImageInfo
        for _, img := range images {
            tags := img.RepoTags
            if len(tags) == 0 {
                tags = []string{"<none>:<none>"}
            }

            imageList = append(imageList, ImageInfo{
                ID:        img.ID,
                ShortID:   img.ID[:12],
                Name:      tags[0],
                Tags:      tags,
                Size:      fmt.Sprintf("%.2f MB", float64(img.Size)/(1024*1024)),
                Created:   time.Unix(img.Created, 0).Format("2006-01-02 15:04:05"),
                IsUsed:    usedImageIDs[img.ID],
            })
        }

        c.JSON(200, imageList)
    })

    // 删除镜像
    r.POST("/images/delete", func(c *gin.Context) {
        var request struct {
            ImageIDs []string `json:"image_ids"`
        }

        if err := c.BindJSON(&request); err != nil {
            detailedErr := logError("PARSE_REQUEST", "", err)
            c.JSON(400, gin.H{"error": detailedErr})
            return
        }

        InfoLogger.Printf("Deleting images: %v", request.ImageIDs)

        cli, err := client.NewClientWithOpts(client.FromEnv)
        if err != nil {
            detailedErr := logError("CREATE_CLIENT", "", err)
            c.JSON(500, gin.H{"error": detailedErr})
            return
        }
        defer cli.Close()

        deleted := []string{}
        errors := []DetailedError{}
        var deletedSize, totalSize int64

        // 计算总大小
        for _, imageID := range request.ImageIDs {
            inspect, _, err := cli.ImageInspectWithRaw(context.Background(), imageID)
            if err == nil {
                totalSize += inspect.Size
            } else {
                errors = append(errors, logError("INSPECT_IMAGE", imageID, err))
            }
        }

        // 删除镜像
        for _, imageID := range request.ImageIDs {
            InfoLogger.Printf("Attempting to delete image: %s", imageID)
            _, err := cli.ImageRemove(context.Background(), imageID, types.ImageRemoveOptions{Force: true})
            if err != nil {
                errors = append(errors, logError("DELETE_IMAGE", imageID, err))
            } else {
                deleted = append(deleted, imageID)
                if inspect, _, err := cli.ImageInspectWithRaw(context.Background(), imageID); err == nil {
                    deletedSize += inspect.Size
                }
                InfoLogger.Printf("Successfully deleted image: %s", imageID)
            }
        }

        status := "success"
        if len(errors) > 0 {
            if len(deleted) > 0 {
                status = "partial"
            } else {
                status = "error"
            }
        }

        c.JSON(200, gin.H{
            "status":      status,
            "deleted":     deleted,
            "errors":      errors,
            "total_count": len(request.ImageIDs),
            "deleted_size": deletedSize,
            "total_size":   totalSize,
        })
    })

    // 添加推送镜像的路由
    r.POST("/images/push", func(c *gin.Context) {
        var config PushConfig
        if err := c.BindJSON(&config); err != nil {
            detailedErr := logError("PARSE_REQUEST", "", err)
            c.JSON(400, gin.H{"error": detailedErr})
            return
        }

        InfoLogger.Printf("Pushing images with proxy type: %s", config.ProxyType)

        setProxy(config.ProxyType, config.ProxyServer)
        defer clearProxy()

        cli, err := client.NewClientWithOpts(
            client.FromEnv,
            client.WithHTTPHeaders(map[string]string{
                "User-Agent": "Docker-Client/19.03.13 (linux)",
            }),
        )
        if err != nil {
            detailedErr := logError("CREATE_CLIENT", "", err)
            c.JSON(500, gin.H{"error": detailedErr})
            return
        }
        defer cli.Close()

        // 登录
        authConfig := types.AuthConfig{
            Username:      config.Username,
            Password:     config.Password,
            ServerAddress: "https://index.docker.io/v1/",
        }

        InfoLogger.Printf("Attempting login for user: %s", config.Username)
        _, err = cli.RegistryLogin(context.Background(), authConfig)
        if err != nil {
            detailedErr := logError("LOGIN", "", err)
            c.JSON(500, gin.H{"error": detailedErr})
            return
        }
        InfoLogger.Printf("Login successful for user: %s", config.Username)

        encodedAuth, err := json.Marshal(authConfig)
        if err != nil {
            detailedErr := logError("ENCODE_AUTH", "", err)
            c.JSON(500, gin.H{"error": detailedErr})
            return
        }

        pushed := []string{}
        errors := []DetailedError{}

        for _, imageID := range config.ImageIDs {
            InfoLogger.Printf("Processing image: %s", imageID)
            inspect, _, err := cli.ImageInspectWithRaw(context.Background(), imageID)
            if err != nil {
                errors = append(errors, logError("INSPECT_IMAGE", imageID, err))
                continue
            }

            for _, tag := range inspect.RepoTags {
                InfoLogger.Printf("Pushing tag: %s", tag)
                reader, err := cli.ImagePush(
                    context.Background(),
                    tag,
                    types.ImagePushOptions{
                        RegistryAuth: base64.URLEncoding.EncodeToString(encodedAuth),
                        All: true,
                    },
                )
                if err != nil {
                    errors = append(errors, logError("PUSH_IMAGE", tag, err))
                    continue
                }
                defer reader.Close()

                decoder := json.NewDecoder(reader)
                for {
                    var event PushProgress
                    if err := decoder.Decode(&event); err != nil {
                        if err == io.EOF {
                            break
                        }
                        errors = append(errors, logError("READ_PROGRESS", tag, err))
                        break
                    }
                    if event.Error != "" {
                        errors = append(errors, DetailedError{
                            Operation: "PUSH_PROGRESS",
                            ImageID:   tag,
                            ErrorCode: "PUSH_FAILED",
                            Message:   event.Error,
                            Timestamp: time.Now().Format("2006-01-02 15:04:05"),
                        })
                        break
                    }
                    // 记录推送进度
                    if event.Status != "" {
                        InfoLogger.Printf("Push progress for %s: %s", tag, event.Status)
                    }
                }
                pushed = append(pushed, tag)
                InfoLogger.Printf("Successfully pushed tag: %s", tag)
            }
        }

        status := "success"
        if len(errors) > 0 {
            if len(pushed) > 0 {
                status = "partial"
            } else {
                status = "error"
            }
        }

        c.JSON(200, gin.H{
            "status":  status,
            "pushed":  pushed,
            "errors":  errors,
        })
    })

    log.Fatal(r.Run(":5526"))  // 使用5526端口，避免与Flask冲突
} 